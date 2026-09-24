from functools import lru_cache

from app.services.text_to_speech_service import TextToSpeechService


@lru_cache
def get_text_to_speech_service() -> TextToSpeechService:
    return TextToSpeechService()