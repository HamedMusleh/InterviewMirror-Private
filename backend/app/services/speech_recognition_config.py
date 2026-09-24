"""
Shared recognizer configuration for both transcription paths.

Kept in one place because the batch service and the live streaming service
must recognise speech identically. If they drift, an answer transcribed live
and the same answer transcribed from its recording produce different text,
and nothing in the system would report the discrepancy.

Two settings here are deliberate:

Language. Interviews are conducted in English, so the recogniser is told so
explicitly rather than left to infer it. Naming the locale is also more
accurate than language detection would be, since detection can misjudge the
opening few words of an answer and there is nothing to detect between.

Profanity. Azure masks profanity by default, replacing words with asterisks.
For an interview transcript that is silent corruption: the masked text is
what analysis, follow-up generation and scoring all read.
"""

import azure.cognitiveservices.speech as speechsdk

from app.core.config import (
    AZURE_SPEECH_KEY,
    AZURE_SPEECH_LANGUAGE,
    AZURE_SPEECH_REGION,
)


def recognition_language() -> str:
    """The locale answers are recognised in."""

    return AZURE_SPEECH_LANGUAGE.strip() or "en-US"


def build_speech_config() -> speechsdk.SpeechConfig:
    """Build a SpeechConfig with the project's recognition settings."""

    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise ValueError("Azure Speech configuration is missing.")

    config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION,
    )

    config.speech_recognition_language = recognition_language()

    # Keep the candidate's own words, asterisks included.
    config.set_profanity(speechsdk.ProfanityOption.Raw)

    return config


def build_recognizer(
    audio_config: speechsdk.audio.AudioConfig,
) -> speechsdk.SpeechRecognizer:
    """Build a recognizer that reads from the given audio source."""

    return speechsdk.SpeechRecognizer(
        speech_config=build_speech_config(),
        audio_config=audio_config,
    )
