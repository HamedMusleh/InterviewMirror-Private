from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonEmptyString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]

Score = Annotated[
    float,
    Field(ge=0, le=100),
]


class CandidateReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)
    interview_id: int = Field(gt=0)
    overall_score: float = Field(ge=0, le=100)
    skill_scores: dict[NonEmptyString, Score]
    strengths: list[NonEmptyString]
    weaknesses: list[NonEmptyString]


class GeneratedReportContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: NonEmptyString
    strengths: list[NonEmptyString]
    areas_for_improvement: list[NonEmptyString]
    recommendation: NonEmptyString


class CandidateReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_evaluation_id: int = Field(gt=0)
    interview_id: int = Field(gt=0)
    overall_score: float = Field(ge=0, le=100)
    skill_scores: dict[NonEmptyString, Score]
    summary: NonEmptyString
    strengths: list[NonEmptyString]
    areas_for_improvement: list[NonEmptyString]
    recommendation: NonEmptyString


class CandidateReportResponse(CandidateReport):
    """
    Complete candidate report contract returned to the frontend by
    POST/GET /api/interviews/{interview_id}/report.
    """

    report_id: int = Field(gt=0)
    candidate_id: int = Field(gt=0)
    candidate_name: NonEmptyString
    job_title: NonEmptyString
    email: NonEmptyString
    phone: str | None = None


class CandidateReportSummary(BaseModel):

    model_config = ConfigDict(extra="forbid")

    report_id: int = Field(gt=0)
    candidate_id: int = Field(gt=0)
    interview_id: int = Field(gt=0)
    candidate_name: NonEmptyString
    job_title: NonEmptyString
    overall_score: float = Field(ge=0, le=100)