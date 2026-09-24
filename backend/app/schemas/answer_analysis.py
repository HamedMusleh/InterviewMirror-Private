from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonEmptyString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]


class PreviousInteraction(BaseModel):
    question: NonEmptyString
    answer: NonEmptyString


class AnswerAnalysisInput(BaseModel):
    interview_id: int = Field(gt=0)
    question_id: int = Field(gt=0)

    role: NonEmptyString
    question: NonEmptyString
    question_type: NonEmptyString

    skill: NonEmptyString | None = None

    answer: NonEmptyString

    previous_interactions: list[PreviousInteraction] = Field(
        default_factory=list
    )


class AnswerAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_quality: Literal["low", "medium", "high"]
    relevant_points: list[str]
    missing_areas: list[str]
    evidence: list[str]
    follow_up_needed: bool
    follow_up_reason: str | None = None
    