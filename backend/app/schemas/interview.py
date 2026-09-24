from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InterviewCreateRequest(BaseModel):
    application_id: int = Field(gt=0)
    scheduled_at: datetime | None = None

    @field_validator("scheduled_at")
    @classmethod
    def scheduled_at_must_include_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("scheduled_at must include a timezone")

        return value


class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    scheduled_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    status: str
    created_at: datetime


class InterviewCreationResponse(BaseModel):
    interview: InterviewResponse
    created: bool

    # How many questions the interview has. Zero means it was created but
    # generation did not succeed, so the caller knows to retry rather than
    # sending the candidate into an empty interview.
    questions_generated: int = 0
