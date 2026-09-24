from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.job_description import JobDescriptionResponse
from app.schemas.resume import ResumeSchema
from app.schemas.screening_score import CategoryName, CategoryScore


MATCHING_CATEGORY_NAMES: tuple[CategoryName, ...] = tuple(
    get_args(CategoryName)
)


MatchStatus = Literal["evaluated", "not_applicable"]
ScreeningCriteriaPayload = dict[str, Any]


class MatchingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MatchingRequest(MatchingModel):
    resume: ResumeSchema
    job_description: JobDescriptionResponse
    # Screening criteria are produced and validated by the Screening Criteria
    # module. Matching consumes that payload without owning its schema.
    screening_criteria: ScreeningCriteriaPayload

    @model_validator(mode="after")
    def validate_matching_ids(self) -> "MatchingRequest":
        candidate_id = self.resume.candidate_id
        if not candidate_id or not candidate_id.strip():
            raise ValueError("resume.candidate_id must not be empty")

        job_id = self.job_description.job_id
        criteria_job_id = self.screening_criteria.get("job_id")

        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError("job_description.job_id must not be empty")

        if not isinstance(criteria_job_id, str) or not criteria_job_id.strip():
            raise ValueError("screening_criteria.job_id must not be empty")

        if self.job_description.job_id != criteria_job_id:
            raise ValueError(
                "job_description.job_id must match screening_criteria.job_id"
            )

        return self


class SkillMatch(MatchingModel):
    required_skill: str
    matched_skill: str | None
    similarity_score: float = Field(ge=0, le=100)
    evidence: str | None


class PreferredSkillMatch(MatchingModel):
    preferred_skill: str
    matched_skill: str | None
    similarity_score: float = Field(ge=0, le=100)
    evidence: str | None


class SkillsMatchingResult(MatchingModel):
    score: float | None = Field(default=None, ge=0, le=100)
    status: MatchStatus
    required: list[SkillMatch]
    preferred: list[PreferredSkillMatch]


class ExperienceMatchingResult(MatchingModel):
    score: float | None = Field(default=None, ge=0, le=100)
    status: MatchStatus
    candidate_years: float = Field(ge=0)
    required_years: float = Field(ge=0)
    level_match: bool | None
    evidence: list[str]


class ProjectMatch(MatchingModel):
    project_name: str
    matched_domain: str | None
    similarity_score: float = Field(ge=0, le=100)
    evidence: str | None


class ProjectsMatchingResult(MatchingModel):
    score: float | None = Field(default=None, ge=0, le=100)
    status: MatchStatus
    matches: list[ProjectMatch]


class EducationMatchingResult(MatchingModel):
    score: float | None = Field(default=None, ge=0, le=100)
    status: MatchStatus
    matched_field: str | None
    evidence: str | None


class ListMatchingResult(MatchingModel):
    score: float | None = Field(default=None, ge=0, le=100)
    status: MatchStatus
    matched: list[str]
    missing: list[str]


class MatchingResults(MatchingModel):
    skills: SkillsMatchingResult
    experience: ExperienceMatchingResult
    projects: ProjectsMatchingResult
    education: EducationMatchingResult
    certifications: ListMatchingResult
    languages: ListMatchingResult
    soft_skills: ListMatchingResult


class MatchingResponse(MatchingModel):
    candidate_id: str
    job_id: str
    matching_results: MatchingResults


class DatabaseMatchingResponse(MatchingResponse):
    """Matching output enriched for the scoring and persistence stages."""

    application_id: int = Field(gt=0)
    job_opportunity_id: int = Field(gt=0)
    criteria_id: int = Field(gt=0)
    category_scores: dict[CategoryName, CategoryScore]
    category_weights: dict[CategoryName, float]
    passing_score: float = Field(ge=0, le=100)
