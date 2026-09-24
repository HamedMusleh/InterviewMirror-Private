from datetime import datetime
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


class CandidateRankingEntry(BaseModel):
    """
    One scored candidate submitted for ranking.

    The score is the candidate's overall interview score on the same
    0-100 scale used by the candidate report, not the 1-10 per-answer
    scale used by the evaluation component.
    """

    model_config = ConfigDict(extra="forbid")

    application_id: int = Field(gt=0)
    interview_id: int = Field(gt=0)
    overall_score: Score


class CandidateRankingRequest(BaseModel):
    """
    The complete set of scored candidates to rank for a job opportunity.

    Storing rankings replaces the job opportunity's existing ranked
    list, so this request must carry every candidate that should appear
    in it - not just the ones whose score changed.
    """

    model_config = ConfigDict(extra="forbid")

    rankings: list[CandidateRankingEntry]


class RankedCandidate(BaseModel):
    """One entry of the ranked candidate list returned to recruiters."""

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    candidate_id: int = Field(gt=0)
    candidate_name: NonEmptyString
    candidate_email: NonEmptyString
    application_id: int = Field(gt=0)
    interview_id: int = Field(gt=0)
    overall_score: Score
    created_at: datetime


class CandidateRankingListResponse(BaseModel):
    """The ranked candidate list of a single job opportunity."""

    model_config = ConfigDict(extra="forbid")

    job_opportunity_id: int = Field(gt=0)
    rankings: list[RankedCandidate]
