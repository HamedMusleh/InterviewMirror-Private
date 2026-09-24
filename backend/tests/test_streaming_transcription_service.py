"""
Tests for StreamingTranscriptionSession.

The session sits between Azure's event callbacks and the WebSocket, so what
matters is that it composes the right transcript at every point: stable
finals plus whichever partial is currently in flight, with the partial
cleared once it is superseded.
"""

import time
from unittest.mock import MagicMock

import azure.cognitiveservices.speech as speechsdk
import pytest

from app.services.streaming_transcription_service import (
    StreamingTranscriptionError,
    StreamingTranscriptionSession,
)


class FakeSignal:
    def __init__(self):
        self._handlers = []

    def connect(self, handler):
        self._handlers.append(handler)

    def fire(self, event):
        for handler in self._handlers:
            handler(event)


class FakeRecognizer:
    def __init__(self):
        self.recognizing = FakeSignal()
        self.recognized = FakeSignal()
        self.canceled = FakeSignal()
        self.session_stopped = FakeSignal()

        self.started = False
        self.stopped = False

    def start_continuous_recognition(self):
        self.started = True

    def stop_continuous_recognition(self):
        self.stopped = True

    def finish_session(self):
        """What Azure does once it has consumed all the buffered audio."""

        self.session_stopped.fire(MagicMock())


def event_for(text, reason=None):
    result = MagicMock()
    result.text = text
    result.reason = (
        reason
        if reason is not None
        else speechsdk.ResultReason.RecognizedSpeech
    )

    event = MagicMock()
    event.result = result

    return event


@pytest.fixture
def session_parts():
    recognizer = FakeRecognizer()
    push_stream = MagicMock()
    updates = []

    # Azure reports the session stopped shortly after the input closes.
    # Wiring that to close() keeps the tests from waiting on the real drain
    # timeout, and mirrors the ordering the service depends on.
    push_stream.close.side_effect = recognizer.finish_session

    session = StreamingTranscriptionSession(
        recognizer=recognizer,
        push_stream=push_stream,
        on_transcript=lambda text, is_final: updates.append((text, is_final)),
    )

    return session, recognizer, push_stream, updates


def test_partial_results_are_visible_immediately(session_parts):
    session, recognizer, _, updates = session_parts

    recognizer.recognizing.fire(event_for("I would start by"))

    assert session.transcript == "I would start by"
    assert updates == [("I would start by", False)]


def test_partial_is_replaced_not_appended(session_parts):
    session, recognizer, _, _ = session_parts

    recognizer.recognizing.fire(event_for("I would"))
    recognizer.recognizing.fire(event_for("I would start"))
    recognizer.recognizing.fire(event_for("I would start by"))

    assert session.transcript == "I would start by"


def test_final_result_supersedes_the_partial(session_parts):
    session, recognizer, _, updates = session_parts

    recognizer.recognizing.fire(event_for("I would start by"))
    recognizer.recognized.fire(
        event_for("I would start by keeping routers thin.")
    )

    assert session.transcript == "I would start by keeping routers thin."
    assert session.final_transcript == (
        "I would start by keeping routers thin."
    )
    assert updates[-1] == (
        "I would start by keeping routers thin.",
        True,
    )


def test_utterances_accumulate_across_pauses(session_parts):
    session, recognizer, _, _ = session_parts

    recognizer.recognized.fire(event_for("First sentence."))
    recognizer.recognized.fire(event_for("Second sentence."))

    assert session.final_transcript == "First sentence. Second sentence."


def test_partial_after_a_final_extends_the_accumulated_text(session_parts):
    session, recognizer, _, _ = session_parts

    recognizer.recognized.fire(event_for("First sentence."))
    recognizer.recognizing.fire(event_for("and then I would"))

    assert session.transcript == "First sentence. and then I would"
    # ... but the stable text is unchanged.
    assert session.final_transcript == "First sentence."


def test_non_speech_finals_are_ignored(session_parts):
    session, recognizer, _, _ = session_parts

    recognizer.recognized.fire(event_for("Real speech."))
    recognizer.recognized.fire(
        event_for("", speechsdk.ResultReason.NoMatch)
    )

    assert session.final_transcript == "Real speech."


def test_audio_chunks_are_written_to_the_push_stream(session_parts):
    session, _, push_stream, _ = session_parts

    session.write(b"chunk-one")
    session.write(b"chunk-two")

    assert push_stream.write.call_count == 2


def test_empty_chunks_are_skipped(session_parts):
    session, _, push_stream, _ = session_parts

    session.write(b"")

    push_stream.write.assert_not_called()


def test_stop_closes_the_stream_before_stopping_recognition(session_parts):
    """Closing first lets Azure flush buffered audio, so the tail of the
    answer is not dropped."""

    session, recognizer, push_stream, _ = session_parts

    order = []

    def on_close():
        order.append("closed stream")
        recognizer.finish_session()

    push_stream.close.side_effect = on_close
    recognizer.stop_continuous_recognition = lambda: order.append(
        "stopped recognition"
    )

    session.start()
    recognizer.recognized.fire(event_for("An answer."))

    assert session.stop() == "An answer."
    assert order == ["closed stream", "stopped recognition"]


def test_writes_after_stop_are_ignored(session_parts):
    session, _, push_stream, _ = session_parts

    session.start()
    session.stop()
    push_stream.write.reset_mock()

    session.write(b"late chunk")

    push_stream.write.assert_not_called()


def test_stop_is_idempotent(session_parts):
    session, _, push_stream, _ = session_parts

    session.start()
    session.stop()
    session.stop()

    assert push_stream.close.call_count == 1


def test_cancellation_surfaces_on_stop(session_parts):
    session, recognizer, _, _ = session_parts

    event = MagicMock()
    event.reason = speechsdk.CancellationReason.Error
    event.error_details = "Speech service failed"

    session.start()
    recognizer.canceled.fire(event)

    with pytest.raises(StreamingTranscriptionError, match="Speech service"):
        session.stop()


def test_stop_waits_for_azure_to_finish_the_buffered_audio(session_parts):
    """
    Audio is written faster than it is transcribed, so tearing the recognizer
    down the instant the stream closes discards the tail of the answer. This
    is the regression guard for that: results that only arrive after close()
    must still make it into the transcript.
    """

    session, recognizer, push_stream, _ = session_parts

    def on_close():
        # Azure delivers the last utterance before reporting the stop.
        recognizer.recognized.fire(event_for("The final sentence."))
        recognizer.finish_session()

    push_stream.close.side_effect = on_close

    session.start()
    recognizer.recognized.fire(event_for("An earlier sentence."))

    assert session.stop() == "An earlier sentence. The final sentence."


def test_stop_gives_up_if_the_session_never_reports_stopping(session_parts):
    """A session that never drains must not block the caller forever."""

    session, _, push_stream, _ = session_parts

    push_stream.close.side_effect = None  # never fires session_stopped

    session.start()
    started = time.monotonic()

    session.stop(drain_timeout_seconds=0.2)

    assert time.monotonic() - started < 5


def test_start_is_idempotent(session_parts):
    session, recognizer, _, _ = session_parts

    recognizer.start_continuous_recognition = MagicMock()

    session.start()
    session.start()

    recognizer.start_continuous_recognition.assert_called_once()
