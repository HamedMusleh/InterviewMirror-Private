"""
Tests for SpeechToTextService.

The service uses continuous recognition rather than ``recognize_once``,
because a single ``recognize_once`` call returns at the first sustained
silence and so transcribes only the opening sentence of a real interview
answer — silently, with no error. Several of these tests exist specifically
to hold that behaviour in place.

Azure delivers results through event handlers, so the fakes here drive those
handlers rather than returning a value.
"""

from unittest.mock import MagicMock, patch

import azure.cognitiveservices.speech as speechsdk
import pytest

from app.services.speech_to_text_service import SpeechToTextService


class FakeSignal:
    """Stand-in for one of the SDK's connectable event signals."""

    def __init__(self):
        self._handlers = []

    def connect(self, handler):
        self._handlers.append(handler)

    def fire(self, event):
        for handler in self._handlers:
            handler(event)


def make_recognition_event(text, reason=None):
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


class FakeRecognizer:
    """
    A recognizer that replays a scripted set of events.

    Everything is emitted synchronously from
    ``start_continuous_recognition``, which is enough for these tests: the
    service waits on an event that the scripted session_stopped will already
    have set by the time it looks.
    """

    def __init__(self, utterances=(), cancellation=None, stop_session=True):
        self.recognizing = FakeSignal()
        self.recognized = FakeSignal()
        self.canceled = FakeSignal()
        self.session_stopped = FakeSignal()

        self._utterances = list(utterances)
        self._cancellation = cancellation
        self._stop_session = stop_session

        self.started = False
        self.stopped = False

    def start_continuous_recognition(self):
        self.started = True

        for utterance in self._utterances:
            if isinstance(utterance, tuple):
                text, reason = utterance
            else:
                text, reason = utterance, None

            self.recognized.fire(make_recognition_event(text, reason))

        if self._cancellation is not None:
            event = MagicMock()
            event.reason = speechsdk.CancellationReason.Error
            event.error_details = self._cancellation
            self.canceled.fire(event)
            return

        if self._stop_session:
            self.session_stopped.fire(MagicMock())

    def stop_continuous_recognition(self):
        self.stopped = True


def run_transcribe(recognizer, timeout=5.0, audio=b"fake-audio-bytes"):
    response = MagicMock()
    response.content = audio
    response.raise_for_status.return_value = None

    with patch(
        "app.services.speech_to_text_service.requests.get",
        return_value=response,
    ), patch(
        "app.services.speech_to_text_service.speechsdk.SpeechRecognizer",
        return_value=recognizer,
    ):
        service = SpeechToTextService(recognition_timeout_seconds=timeout)

        return service.transcribe("https://example.com/answer.webm")


def test_transcribe_returns_recognized_text():
    result = run_transcribe(
        FakeRecognizer(["I used FastAPI to build REST APIs."])
    )

    assert result == "I used FastAPI to build REST APIs."


def test_transcribe_joins_every_utterance_in_the_recording():
    """The whole point of continuous recognition: nothing after the first
    pause is thrown away."""

    recognizer = FakeRecognizer(
        [
            "I would start by keeping the routers thin.",
            "The router declares its collaborators using Depends.",
            "On the database side, I let the request own the transaction.",
        ]
    )

    result = run_transcribe(recognizer)

    assert result == (
        "I would start by keeping the routers thin. "
        "The router declares its collaborators using Depends. "
        "On the database side, I let the request own the transaction."
    )


def test_transcribe_starts_and_stops_continuous_recognition():
    recognizer = FakeRecognizer(["Some answer."])

    run_transcribe(recognizer)

    assert recognizer.started is True
    assert recognizer.stopped is True


def test_transcribe_ignores_non_speech_results():
    recognizer = FakeRecognizer(
        [
            ("Real speech.", speechsdk.ResultReason.RecognizedSpeech),
            ("", speechsdk.ResultReason.NoMatch),
        ]
    )

    assert run_transcribe(recognizer) == "Real speech."


def test_transcribe_downloads_audio_from_given_url():
    response = MagicMock()
    response.content = b"fake-audio-bytes"
    response.raise_for_status.return_value = None

    mock_get = MagicMock(return_value=response)

    with patch(
        "app.services.speech_to_text_service.requests.get", mock_get
    ), patch(
        "app.services.speech_to_text_service.speechsdk.SpeechRecognizer",
        return_value=FakeRecognizer(["Some answer."]),
    ):
        SpeechToTextService().transcribe("https://example.com/answer.webm")

    mock_get.assert_called_once_with(
        "https://example.com/answer.webm", timeout=30
    )


def test_transcribe_raises_when_no_speech_recognized():
    with pytest.raises(RuntimeError, match="could not understand the audio"):
        run_transcribe(FakeRecognizer([]))


def test_transcribe_raises_error_when_azure_cancels():
    recognizer = FakeRecognizer(cancellation="Speech service failed")

    with pytest.raises(RuntimeError, match="Speech recognition failed"):
        run_transcribe(recognizer)


def test_transcribe_raises_when_recognition_never_finishes():
    """A session that never stops must not hang the caller forever."""

    recognizer = FakeRecognizer(["Partial."], stop_session=False)

    with pytest.raises(RuntimeError, match="did not complete within"):
        run_transcribe(recognizer, timeout=0.2)


def test_transcribe_raises_when_speech_config_missing():
    with patch(
        "app.services.speech_to_text_service.AZURE_SPEECH_KEY", ""
    ):
        service = SpeechToTextService()

        with pytest.raises(
            ValueError,
            match="Azure Speech configuration is missing",
        ):
            service.transcribe("https://example.com/answer.webm")
