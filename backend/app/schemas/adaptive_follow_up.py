from pydantic import BaseModel, field_validator, model_validator


class FollowUpQuestionRequest(BaseModel):
    question_id: int
    question: str
    answer: str
    question_type: str
    skill: str | None = None
    missing_areas: list[str] = []
    follow_up_needed: bool
    follow_up_reason: str | None = None

    @field_validator("question", "answer", "question_type")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty.")
        return v.strip()

    @model_validator(mode="after")
    def reason_required_when_needed(self):
        if self.follow_up_needed and not (
            self.follow_up_reason and self.follow_up_reason.strip()
        ):
            raise ValueError(
                "follow_up_reason is required when follow_up_needed is true."
            )
        return self


class GeneratedFollowUp(BaseModel):
    question: str


class FollowUpQuestionResponse(BaseModel):
    parent_question_id: int
    question: str
    category: str
    skill: str | None = None