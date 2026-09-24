from datetime import timedelta
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest
from pydantic import ValidationError

from app.schemas.speech import TextToSpeechRequest


def test_valid_text_to_speech_request():
    request = TextToSpeechRequest(
        text="Explain your experience with FastAPI."
    )

    assert request.text == "Explain your experience with FastAPI."


def test_strips_text_whitespace():
    request = TextToSpeechRequest(
        text="  Explain your experience with FastAPI.  "
    )

    assert request.text == "Explain your experience with FastAPI."


def test_rejects_empty_text():
    with pytest.raises(ValidationError):
        TextToSpeechRequest(text="")


def test_rejects_whitespace_only_text():
    with pytest.raises(ValidationError):
        TextToSpeechRequest(text="     ")

from unittest.mock import MagicMock, patch

from app.services.text_to_speech_service import TextToSpeechService


def test_synthesize_returns_audio_bytes():
    fake_audio = b"fake-mp3-audio"

    mock_result = MagicMock()
    mock_result.reason = (
        __import__(
            "azure.cognitiveservices.speech",
            fromlist=["ResultReason"],
        ).ResultReason.SynthesizingAudioCompleted
    )
    mock_result.audio_data = fake_audio

    mock_synthesizer = MagicMock()
    mock_synthesizer.speak_text_async.return_value.get.return_value = (
        mock_result
    )

    with patch(
        "app.services.text_to_speech_service.speechsdk.SpeechSynthesizer",
        return_value=mock_synthesizer,
    ):
        service = TextToSpeechService()
        result = service.synthesize("Tell me about yourself.")

    assert result == fake_audio
    mock_synthesizer.speak_text_async.assert_called_once_with(
        "Tell me about yourself."
    )

def test_synthesize_raises_error_when_azure_cancels():
    import azure.cognitiveservices.speech as speechsdk

    mock_result = MagicMock()
    mock_result.reason = speechsdk.ResultReason.Canceled

    mock_synthesizer = MagicMock()
    mock_synthesizer.speak_text_async.return_value.get.return_value = (
        mock_result
    )

    mock_cancellation = MagicMock()
    mock_cancellation.reason = "Error"
    mock_cancellation.error_details = "Speech service failed"

    with patch(
        "app.services.text_to_speech_service.speechsdk.SpeechSynthesizer",
        return_value=mock_synthesizer,
    ), patch(
        "app.services.text_to_speech_service."
        "speechsdk.SpeechSynthesisCancellationDetails",
        return_value=mock_cancellation,
    ):
        service = TextToSpeechService()

        with pytest.raises(
            RuntimeError,
            match="Speech synthesis failed",
        ):
            service.synthesize("Tell me about yourself.")


# --- the animated line -------------------------------------------------
#
# `synthesize_line` exists so the avatar can lip-sync to exactly the audio
# being played. Azure raises the mouth-shape events during synthesis rather
# than returning them, so these tests fake a synthesizer that fires them, and
# check the two things that would silently break the animation: losing the
# events by connecting too late, and reporting their offsets in the wrong
# unit.


class FakeSignal:
    """Stands in for an SDK event, which is connected to rather than called."""

    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def fire(self, event):
        for callback in self.callbacks:
            callback(event)


class FakeSynthesizer:
    """
    Fires its events from inside `speak_ssml_async`, exactly as Azure does.

    That timing is the point: a service that connected its callbacks after
    starting synthesis would pass a test where the events are replayed
    afterwards, and produce a motionless avatar in production.
    """

    def __init__(self, result, visemes=(), words=()):
        self.viseme_received = FakeSignal()
        self.synthesis_word_boundary = FakeSignal()
        self.spoken_ssml = None

        self._result = result
        self._visemes = list(visemes)
        self._words = list(words)

    def speak_ssml_async(self, ssml):
        self.spoken_ssml = ssml

        for viseme in self._visemes:
            self.viseme_received.fire(viseme)

        for word in self._words:
            self.synthesis_word_boundary.fire(word)

        return SimpleNamespace(get=lambda: self._result)


def completed_result(audio=b"mp3", duration_seconds=1.5):
    import azure.cognitiveservices.speech as speechsdk

    return SimpleNamespace(
        reason=speechsdk.ResultReason.SynthesizingAudioCompleted,
        audio_data=audio,
        audio_duration=timedelta(seconds=duration_seconds),
    )


def viseme(viseme_id, offset_ms):
    return SimpleNamespace(
        viseme_id=viseme_id,
        audio_offset=offset_ms * 10_000,
    )


def word(text, offset_ms, duration_ms):
    return SimpleNamespace(
        text=text,
        audio_offset=offset_ms * 10_000,
        duration=timedelta(milliseconds=duration_ms),
    )


def synthesize_line(text="Tell me about yourself.", style="chat", **kwargs):
    synthesizer = FakeSynthesizer(**kwargs)

    with patch(
        "app.services.text_to_speech_service.speechsdk.SpeechSynthesizer",
        return_value=synthesizer,
    ):
        spoken = TextToSpeechService().synthesize_line(text, style)

    return spoken, synthesizer


def test_synthesize_line_returns_audio_with_its_viseme_timeline():
    spoken, _ = synthesize_line(
        result=completed_result(audio=b"fake-mp3"),
        visemes=[viseme(21, 0), viseme(6, 120), viseme(2, 260)],
    )

    assert spoken.audio_data == b"fake-mp3"
    assert [(mark.viseme_id, mark.offset_ms) for mark in spoken.visemes] == [
        (21, 0),
        (6, 120),
        (2, 260),
    ]


def test_viseme_offsets_are_converted_from_ticks_to_milliseconds():
    """
    Azure reports 100-nanosecond ticks. Passing those through unconverted
    would put every mouth shape ten thousand times too late.
    """

    spoken, _ = synthesize_line(
        result=completed_result(),
        visemes=[viseme(4, 500)],
    )

    assert spoken.visemes[0].offset_ms == 500


def test_word_boundaries_are_captured_with_their_durations():
    spoken, _ = synthesize_line(
        result=completed_result(),
        words=[word("Tell", 0, 200), word("me", 200, 90)],
    )

    assert [(mark.text, mark.offset_ms, mark.duration_ms) for mark in
            spoken.words] == [("Tell", 0, 200), ("me", 200, 90)]


def test_marks_are_sorted_even_if_the_sdk_raises_them_out_of_order():
    spoken, _ = synthesize_line(
        result=completed_result(),
        visemes=[viseme(2, 260), viseme(21, 0), viseme(6, 120)],
    )

    assert [mark.offset_ms for mark in spoken.visemes] == [0, 120, 260]


def test_duration_comes_from_the_result_when_azure_reports_one():
    spoken, _ = synthesize_line(
        result=completed_result(duration_seconds=2.0),
        visemes=[viseme(2, 260)],
    )

    assert spoken.duration_ms == 2000


def test_duration_falls_back_to_the_last_viseme_when_azure_reports_none():
    result = completed_result()
    result.audio_duration = None

    spoken, _ = synthesize_line(
        result=result,
        visemes=[viseme(21, 0), viseme(2, 640)],
    )

    assert spoken.duration_ms == 640


def test_the_requested_style_is_applied_to_the_voice():
    _, synthesizer = synthesize_line(
        style="empathetic",
        result=completed_result(),
    )

    assert 'style="empathetic"' in synthesizer.spoken_ssml
    assert "mstts:viseme" in synthesizer.spoken_ssml


def test_an_unsupported_style_falls_back_instead_of_being_ignored():
    """
    Azure does not reject an unknown style, it drops it. Catching it here is
    the only way a typo becomes visible rather than quietly flattening the
    interviewer's delivery.
    """

    _, synthesizer = synthesize_line(
        style="sarcastic",
        result=completed_result(),
    )

    assert 'style="chat"' in synthesizer.spoken_ssml


def test_a_follow_on_segment_is_spoken_after_a_real_pause():
    """
    The bridge and the question it leads into must not run together.

    Spoken as one uninterrupted string they land as a single breathless
    announcement, which is exactly what makes the interviewer sound like it
    is reading from a form rather than responding to the person in front of
    it.
    """

    _, synthesizer = synthesize_line(
        text="Glad to hear it.",
        result=completed_result(),
        # `then` and `pause_ms` are positional on the service call below.
    )

    assert "break" not in synthesizer.spoken_ssml

    synthesizer = FakeSynthesizer(result=completed_result())

    with patch(
        "app.services.text_to_speech_service.speechsdk.SpeechSynthesizer",
        return_value=synthesizer,
    ):
        TextToSpeechService().synthesize_line(
            "Glad to hear it.",
            "chat",
            "Tell me about a system you designed.",
            700,
        )

    assert '<break time="700ms"/>' in synthesizer.spoken_ssml
    assert "Glad to hear it." in synthesizer.spoken_ssml
    assert "Tell me about a system you designed." in synthesizer.spoken_ssml

    # The break sits between the two, not before or after both.
    ssml = synthesizer.spoken_ssml
    assert ssml.index("Glad") < ssml.index("<break") < ssml.index("Tell me")

    ElementTree.fromstring(ssml)


def test_a_follow_on_segment_is_escaped_too():
    synthesizer = FakeSynthesizer(result=completed_result())

    with patch(
        "app.services.text_to_speech_service.speechsdk.SpeechSynthesizer",
        return_value=synthesizer,
    ):
        TextToSpeechService().synthesize_line(
            "Understood.",
            "chat",
            "Have you used R&D budgets before?",
        )

    assert "R&amp;D" in synthesizer.spoken_ssml
    ElementTree.fromstring(synthesizer.spoken_ssml)


def test_the_spoken_text_is_xml_escaped():
    """A question mentioning R&D or a < operator must not break the SSML."""

    _, synthesizer = synthesize_line(
        text="Have you worked in R&D on <T> generics?",
        result=completed_result(),
    )

    assert "R&amp;D" in synthesizer.spoken_ssml
    assert "&lt;T&gt;" in synthesizer.spoken_ssml

    ElementTree.fromstring(synthesizer.spoken_ssml)