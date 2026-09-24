import threading

import azure.cognitiveservices.speech as speechsdk
import requests

from app.core.config import (
    AZURE_SPEECH_KEY,
    AZURE_SPEECH_REGION,
)
from app.services.speech_recognition_config import (
    build_recognizer as build_configured_recognizer,
)


# A candidate answer can run for minutes, and recognition streams in roughly
# real time, so the wait has to be generous. It is a deadlock guard, not an
# expected duration.
DEFAULT_RECOGNITION_TIMEOUT_SECONDS = 600.0


class SpeechToTextService:
    """
    Transcribe a recorded interview answer using Azure AI Speech.

    Uses continuous recognition rather than ``recognize_once``. A single
    ``recognize_once`` call returns at the first sustained silence (or after
    about fifteen seconds), which for a real interview answer means the
    stored transcript is the opening sentence and nothing else — with no
    error raised to signal the loss. Continuous recognition keeps going to
    the end of the audio and emits one result per utterance, which are joined
    back together here.
    """

    def __init__(
        self,
        recognition_timeout_seconds: float = (
            DEFAULT_RECOGNITION_TIMEOUT_SECONDS
        ),
    ) -> None:
        self._recognition_timeout_seconds = recognition_timeout_seconds

    def transcribe(self, audio_url: str) -> str:
        """
        Convert a candidate's recorded answer into text.

        ``audio_url`` is expected to point at a compressed audio recording
        (e.g. the webm/opus output of the browser's MediaRecorder). The audio
        bytes are downloaded and streamed into Azure Speech's
        compressed-audio input, which requires GStreamer on the host to
        decode non-WAV formats.
        """

        if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
            raise ValueError(
                "Azure Speech configuration is missing."
            )

        audio_bytes = self._download_audio(audio_url)

        recognizer = self._build_recognizer(audio_bytes)

        segments: list[str] = []
        cancellation_error: list[str] = []
        finished = threading.Event()

        def on_recognized(event) -> None:
            result = event.result

            if (
                result.reason == speechsdk.ResultReason.RecognizedSpeech
                and result.text
            ):
                segments.append(result.text)

        def on_canceled(event) -> None:
            if event.reason == speechsdk.CancellationReason.Error:
                cancellation_error.append(
                    f"{event.reason} - {event.error_details}"
                )

            finished.set()

        def on_session_stopped(_event) -> None:
            finished.set()

        recognizer.recognized.connect(on_recognized)
        recognizer.canceled.connect(on_canceled)
        recognizer.session_stopped.connect(on_session_stopped)

        recognizer.start_continuous_recognition()

        try:
            completed = finished.wait(
                timeout=self._recognition_timeout_seconds
            )
        finally:
            recognizer.stop_continuous_recognition()

        if cancellation_error:
            raise RuntimeError(
                f"Speech recognition failed: {cancellation_error[0]}"
            )

        if not completed:
            raise RuntimeError(
                "Speech recognition did not complete within "
                f"{self._recognition_timeout_seconds} seconds."
            )

        if not segments:
            raise RuntimeError(
                "Speech recognition could not understand the audio."
            )

        return " ".join(segments)

    def _build_recognizer(
        self,
        audio_bytes: bytes,
    ) -> speechsdk.SpeechRecognizer:
        stream_format = speechsdk.audio.AudioStreamFormat(
            compressed_stream_format=(
                speechsdk.AudioStreamContainerFormat.ANY
            )
        )

        push_stream = speechsdk.audio.PushAudioInputStream(
            stream_format
        )

        push_stream.write(audio_bytes)
        push_stream.close()

        return build_configured_recognizer(
            speechsdk.audio.AudioConfig(stream=push_stream)
        )

    def _download_audio(self, audio_url: str) -> bytes:
        response = requests.get(audio_url, timeout=30)
        response.raise_for_status()

        return response.content
