"""
The interviewer's voice.

Two entry points, deliberately kept apart. `synthesize` is the plain
text-to-audio call the rest of the app already uses. `synthesize_line` is the
one the interview room uses, and it returns more than audio: it also returns
the viseme timeline Azure produces as a by-product of synthesis.

That timeline is what separates an avatar that talks from a picture with a
sound file playing behind it. Azure already knows which mouth shape belongs
to every instant of the audio it just generated, so the alternative -- having
the browser infer mouth movement from the waveform's amplitude -- would be
throwing away exact information and replacing it with a guess that always
reads as badly dubbed.
"""

from dataclasses import dataclass, field
from xml.sax.saxutils import escape

import azure.cognitiveservices.speech as speechsdk

from app.core.config import (
    AZURE_SPEECH_KEY,
    AZURE_SPEECH_REGION,
)
from app.schemas.speech import VisemeMark, WordMark


# Chosen for its expressive styles. A single flat delivery for greeting,
# question and closing alike is the thing that makes a synthetic interviewer
# feel like a kiosk, and this voice can be told which register to use.
INTERVIEWER_VOICE = "en-US-JennyNeural"

# Styles the voice actually supports. An unsupported style is not rejected by
# Azure, it is silently ignored, so an unnoticed typo would quietly cost the
# expressiveness this whole class exists to provide.
SUPPORTED_STYLES = frozenset(
    {
        "assistant",
        "chat",
        "cheerful",
        "customerservice",
        "empathetic",
        "excited",
        "friendly",
        "hopeful",
        "newscast",
        "sad",
        "unfriendly",
        "whispering",
    }
)

DEFAULT_STYLE = "chat"

# Slightly under the default. Interview questions land better with a beat of
# room around them, and the candidate is listening in order to decide what to
# say next.
SPEAKING_RATE = "-3%"

# The beat between the interviewer's own words and the question it reads out.
# Long enough to hear as two separate thoughts, short enough not to read as
# the audio having stopped.
DEFAULT_PAUSE_MS = 500

# Azure reports offsets in 100-nanosecond ticks.
TICKS_PER_MILLISECOND = 10_000


@dataclass
class SynthesizedSpeech:
    """Audio together with the marks measured against that exact audio."""

    audio_data: bytes
    duration_ms: int = 0
    visemes: list[VisemeMark] = field(default_factory=list)
    words: list[WordMark] = field(default_factory=list)


class TextToSpeechService:

    def synthesize(self, text: str) -> bytes:
        """
        Convert question text into MP3 audio using Azure AI Speech.
        """

        synthesizer = self._build_synthesizer()

        result = synthesizer.speak_text_async(text).get()

        return self._audio_from(result)

    def synthesize_line(
        self,
        text: str,
        style: str = DEFAULT_STYLE,
        then: str | None = None,
        pause_ms: int = DEFAULT_PAUSE_MS,
    ) -> SynthesizedSpeech:
        """
        Speak a line, and report how the mouth moved while speaking it.

        The callbacks are connected before synthesis starts, because Azure
        raises them as the audio is produced rather than afterwards. They run
        on the SDK's own threads, so they do nothing but append.
        """

        synthesizer = self._build_synthesizer()

        visemes: list[VisemeMark] = []
        words: list[WordMark] = []

        def on_viseme(event) -> None:
            visemes.append(
                VisemeMark(
                    viseme_id=int(event.viseme_id),
                    offset_ms=(
                        int(event.audio_offset) // TICKS_PER_MILLISECOND
                    ),
                )
            )

        def on_word_boundary(event) -> None:
            words.append(
                WordMark(
                    text=str(event.text),
                    offset_ms=(
                        int(event.audio_offset) // TICKS_PER_MILLISECOND
                    ),
                    duration_ms=_duration_ms(event),
                )
            )

        synthesizer.viseme_received.connect(on_viseme)
        synthesizer.synthesis_word_boundary.connect(on_word_boundary)

        result = synthesizer.speak_ssml_async(
            self._build_ssml(text, style, then, pause_ms)
        ).get()

        audio_data = self._audio_from(result)

        visemes.sort(key=lambda mark: mark.offset_ms)
        words.sort(key=lambda mark: mark.offset_ms)

        return SynthesizedSpeech(
            audio_data=audio_data,
            duration_ms=_result_duration_ms(result, visemes),
            visemes=visemes,
            words=words,
        )

    def _build_ssml(
        self,
        text: str,
        style: str,
        then: str | None = None,
        pause_ms: int = DEFAULT_PAUSE_MS,
    ) -> str:
        """
        Wrap the line so the voice knows how to say it, not only what.

        The `mstts:viseme` element asks for mouth-shape events explicitly
        rather than relying on the default, so the animation data cannot
        quietly stop arriving if that default ever changes.

        A `then` segment is spoken after an explicit pause. Azure keeps
        counting audio offsets across a break, so the viseme timeline stays
        continuous and the mouth simply rests through the gap.
        """

        chosen_style = style if style in SUPPORTED_STYLES else DEFAULT_STYLE

        spoken = escape(text)

        if then:
            spoken += f'<break time="{max(pause_ms, 0)}ms"/>{escape(then)}'

        return (
            '<speak version="1.0" '
            'xmlns="http://www.w3.org/2001/10/synthesis" '
            'xmlns:mstts="https://www.w3.org/2001/mstts" '
            'xml:lang="en-US">'
            f'<voice name="{INTERVIEWER_VOICE}">'
            '<mstts:viseme type="redlips_front"/>'
            f'<mstts:express-as style="{chosen_style}" styledegree="1">'
            f'<prosody rate="{SPEAKING_RATE}">{spoken}</prosody>'
            "</mstts:express-as>"
            "</voice>"
            "</speak>"
        )

    def _build_synthesizer(self) -> speechsdk.SpeechSynthesizer:
        if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
            raise ValueError(
                "Azure Speech configuration is missing."
            )

        speech_config = speechsdk.SpeechConfig(
            subscription=AZURE_SPEECH_KEY,
            region=AZURE_SPEECH_REGION,
        )

        speech_config.speech_synthesis_voice_name = INTERVIEWER_VOICE

        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        )

        return speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=None,
        )

    def _audio_from(self, result) -> bytes:
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return bytes(result.audio_data)

        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation = speechsdk.SpeechSynthesisCancellationDetails(
                result
            )

            raise RuntimeError(
                f"Speech synthesis failed: "
                f"{cancellation.reason} - "
                f"{cancellation.error_details}"
            )

        raise RuntimeError(
            "Speech synthesis did not complete successfully."
        )


def _duration_ms(event) -> int:
    """
    Read a word's duration, which the SDK reports as a timedelta.

    Older SDK builds expose ticks instead, and a missing duration is not
    worth failing a whole interview line over, so both are tolerated.
    """

    duration = getattr(event, "duration", None)

    if duration is None:
        return 0

    total_seconds = getattr(duration, "total_seconds", None)

    if callable(total_seconds):
        return int(total_seconds() * 1000)

    try:
        return int(duration) // TICKS_PER_MILLISECOND
    except (TypeError, ValueError):
        return 0


def _result_duration_ms(result, visemes: list[VisemeMark]) -> int:
    """
    How long the audio runs.

    Falls back to the last mouth shape's offset, which is never later than
    the end of the audio, so a missing duration degrades to a slightly short
    estimate rather than to zero.
    """

    duration = getattr(result, "audio_duration", None)
    total_seconds = getattr(duration, "total_seconds", None)

    if callable(total_seconds):
        measured = int(total_seconds() * 1000)

        if measured > 0:
            return measured

    return visemes[-1].offset_ms if visemes else 0
