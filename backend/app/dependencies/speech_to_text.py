from functools import lru_cache

from app.services.speech_to_text_service import SpeechToTextService


@lru_cache
def get_speech_to_text_service() -> SpeechToTextService:
    return SpeechToTextService()
