"""
Live transcription of a candidate's answer while they are still speaking.

The batch path (SpeechToTextService) transcribes a finished recording. Turn
detection cannot wait for that: the decision about whether the candidate has
finished has to be made *during* the answer, which means the transcript has
to arrive during the answer too.

This wraps Azure's continuous recognition around a push stream that audio
chunks are fed into as they arrive from the browser. Azure emits two kinds
of event, and both matter here:

    recognizing -> an unstable partial for the utterance in progress
    recognized  -> the stable final text for a completed utterance

The partials are what make endpointing responsive; the finals are what get
stored. The accumulated transcript is the finals joined together plus
whatever partial is currently in flight.
"""

import threading
from collections.abc import Callable

import azure.cognitiveservices.speech as speechsdk

from app.services.speech_recognition_config import (
    build_recognizer as build_configured_recognizer,
)


DEFAULT_DRAIN_TIMEOUT_SECONDS = 60.0
"""How long to let Azure finish transcribing buffered audio after the
candidate stops speaking. Only a deadlock guard, not an expected wait."""


TranscriptListener = Callable[[str, bool], None]
"""Called with (transcript_so_far, is_final) on every recognition event."""


class StreamingTranscriptionError(RuntimeError):
    """Raised when Azure cancels the recognition session with an error."""


def build_push_stream() -> speechsdk.audio.PushAudioInputStream:
    """
    Build a push stream that accepts the browser's compressed audio.

    MediaRecorder with a timeslice emits one continuous container stream in
    chunks, not a series of standalone files, so the chunks can be written
    straight through in order. Decoding them needs GStreamer on the host.
    """

    stream_format = speechsdk.audio.AudioStreamFormat(
        compressed_stream_format=speechsdk.AudioStreamContainerFormat.ANY
    )

    return speechsdk.audio.PushAudioInputStream(stream_format)


def build_recognizer(
    push_stream: speechsdk.audio.PushAudioInputStream,
) -> speechsdk.SpeechRecognizer:
    """Build a recognizer reading from the given push stream."""

    return build_configured_recognizer(
        speechsdk.audio.AudioConfig(stream=push_stream)
    )


class StreamingTranscriptionSession:
    """
    One live transcription for one answer.

    The recognizer and push stream are injected so the session can be tested
    without Azure. Azure delivers its events on its own threads, so all
    mutable state here is guarded by a lock and the listener may be invoked
    from a background thread.
    """

    def __init__(
        self,
        recognizer,
        push_stream,
        on_transcript: TranscriptListener | None = None,
    ) -> None:
        self._recognizer = recognizer
        self._push_stream = push_stream
        self._on_transcript = on_transcript

        self._lock = threading.Lock()
        self._final_segments: list[str] = []
        self._partial = ""
        self._error: str | None = None
        self._started = False
        self._stopped = False

        # Set once Azure has consumed every byte written to the stream.
        self._drained = threading.Event()

        self._recognizer.recognizing.connect(self._handle_recognizing)
        self._recognizer.recognized.connect(self._handle_recognized)
        self._recognizer.canceled.connect(self._handle_canceled)
        self._recognizer.session_stopped.connect(self._handle_session_stopped)

    # ---------------------------------------------------------------- state

    @property
    def transcript(self) -> str:
        """Everything recognised so far, including the in-flight partial."""

        with self._lock:
            return self._compose_unlocked()

    @property
    def final_transcript(self) -> str:
        """Only the stable text. This is what gets stored."""

        with self._lock:
            return " ".join(self._final_segments).strip()

    @property
    def error(self) -> str | None:
        with self._lock:
            return self._error

    def _compose_unlocked(self) -> str:
        parts = [*self._final_segments]

        if self._partial:
            parts.append(self._partial)

        return " ".join(part for part in parts if part).strip()

    # ------------------------------------------------------------- lifecycle

    def start(self) -> None:
        if self._started:
            return

        self._started = True
        self._recognizer.start_continuous_recognition()

    def write(self, chunk: bytes) -> None:
        """Feed one audio chunk from the browser into recognition."""

        if self._stopped or not chunk:
            return

        self._push_stream.write(chunk)

    def stop(
        self,
        drain_timeout_seconds: float = DEFAULT_DRAIN_TIMEOUT_SECONDS,
    ) -> str:
        """
        Close the stream, let recognition finish, and return the transcript.

        The wait in the middle is load-bearing. Audio is written faster than
        Azure transcribes it, so at the moment the candidate stops speaking
        there is always some already-sent audio that has not been recognised
        yet. Closing the stream signals end-of-input, but tearing the
        recognizer down straight afterwards discards whatever was still in
        flight — which silently drops the end of the answer, and the more
        audio is buffered the more is lost.

        So after closing, wait for Azure to report the session stopped, which
        it does once it has consumed everything. The timeout only guards
        against a session that never reports at all.
        """

        if self._stopped:
            return self.final_transcript

        self._stopped = True

        try:
            self._push_stream.close()

            if self._started:
                self._drained.wait(timeout=drain_timeout_seconds)
        finally:
            if self._started:
                self._recognizer.stop_continuous_recognition()

        if self._error:
            raise StreamingTranscriptionError(self._error)

        return self.final_transcript

    # ---------------------------------------------------------------- events

    def _handle_recognizing(self, event) -> None:
        text = getattr(event.result, "text", "") or ""

        with self._lock:
            self._partial = text
            composed = self._compose_unlocked()

        self._emit(composed, False)

    def _handle_recognized(self, event) -> None:
        result = event.result

        if result.reason != speechsdk.ResultReason.RecognizedSpeech:
            return

        text = (result.text or "").strip()

        with self._lock:
            self._partial = ""

            if text:
                self._final_segments.append(text)

            composed = self._compose_unlocked()

        self._emit(composed, True)

    def _handle_canceled(self, event) -> None:
        if event.reason == speechsdk.CancellationReason.Error:
            with self._lock:
                self._error = f"{event.reason} - {event.error_details}"

        # Cancellation ends the session either way, including the ordinary
        # end-of-stream case; nothing more is coming.
        self._drained.set()

    def _handle_session_stopped(self, _event) -> None:
        self._drained.set()

    def _emit(self, transcript: str, is_final: bool) -> None:
        if self._on_transcript is not None:
            self._on_transcript(transcript, is_final)
