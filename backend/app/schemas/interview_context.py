from pydantic import BaseModel, model_validator


class InterviewContextRequest(BaseModel):
    interview_id: int
    question_id: int
    audio_url: str | None = None
    video_url: str | None = None
    answer_text: str | None = None

    @model_validator(mode="after")
    def check_has_answer_source(self) -> "InterviewContextRequest":
        if not (self.audio_url or self.video_url or self.answer_text):
            raise ValueError(
                "One of audio_url, video_url, or answer_text is required"
            )

        return self


class PriorInteraction(BaseModel):
    question: str
    answer: str


class InterviewContext(BaseModel):
    interview_id: int
    question_id: int
    role: str
    question: str
    question_type: str
    skill: str | None
    answer: str
    previous_interactions: list[PriorInteraction]
