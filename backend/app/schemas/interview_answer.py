from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AudioAnswerCreate(BaseModel):
    question_id: int
    audio_url: str


class InterviewAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    answer_text: str | None
    audio_url: str | None
    video_url: str | None
    transcript: str | None
    answered_at: datetime