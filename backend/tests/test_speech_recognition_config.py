"""
Tests for the shared recognizer configuration.

Both settings covered here corrupt transcripts silently when wrong, which is
why they are pinned. A recognizer left on its defaults masks profanity,
replacing a candidate's own words with asterisks. Neither that nor a wrong
locale raises anything: the damaged text is simply what analysis, follow-ups
and scoring go on to read.
"""

from unittest.mock import MagicMock, patch

import azure.cognitiveservices.speech as speechsdk

from app.services import speech_recognition_config as config


def test_the_configured_locale_is_used():
    with patch.object(config, "AZURE_SPEECH_LANGUAGE", "en-GB"):
        assert config.recognition_language() == "en-GB"


def test_surrounding_whitespace_is_tolerated():
    with patch.object(config, "AZURE_SPEECH_LANGUAGE", "  en-US  "):
        assert config.recognition_language() == "en-US"


def test_english_is_the_fallback_when_nothing_is_configured():
    with patch.object(config, "AZURE_SPEECH_LANGUAGE", ""):
        assert config.recognition_language() == "en-US"


def test_the_recognition_language_is_set_explicitly():
    """
    Stated rather than inferred. Azure would default to en-US anyway, but
    leaving it implicit hides the assumption from anyone reading the code.
    """

    speech_config = MagicMock()

    with patch.object(
        config.speechsdk, "SpeechConfig", return_value=speech_config
    ), patch.object(config, "AZURE_SPEECH_LANGUAGE", "en-US"):
        config.build_speech_config()

    assert speech_config.speech_recognition_language == "en-US"


def test_profanity_is_not_masked():
    """Masked profanity silently rewrites the candidate's own words."""

    speech_config = MagicMock()

    with patch.object(
        config.speechsdk, "SpeechConfig", return_value=speech_config
    ):
        config.build_speech_config()

    speech_config.set_profanity.assert_called_once_with(
        speechsdk.ProfanityOption.Raw
    )


def test_missing_credentials_raise_rather_than_producing_a_dead_recognizer():
    with patch.object(config, "AZURE_SPEECH_KEY", ""):
        try:
            config.build_speech_config()
        except ValueError as exc:
            assert "Azure Speech configuration is missing" in str(exc)
        else:
            raise AssertionError("expected a ValueError")


def test_the_recognizer_reads_from_the_given_audio_source():
    audio_config = MagicMock()

    with patch.object(
        config.speechsdk, "SpeechConfig", return_value=MagicMock()
    ), patch.object(config.speechsdk, "SpeechRecognizer") as recognizer:
        config.build_recognizer(audio_config)

    assert recognizer.call_args.kwargs["audio_config"] is audio_config
