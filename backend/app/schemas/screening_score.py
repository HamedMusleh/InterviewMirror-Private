from typing import Annotated, Literal, get_args

from pydantic import BaseModel, Field, StringConstraints, model_validator


RequiredCategoryName = Literal[
    "skills",
    "experience",
    "education",
    "projects",
    "certifications",
    "languages",
    "soft_skills",
]

NonEmptyId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]

CategoryName = RequiredCategoryName

REQUIRED_CATEGORIES: frozenset[str] = frozenset(
    get_args(RequiredCategoryName)
)


class CategoryScore(BaseModel):
    score: float | None = Field(default=None, ge=0, le=100)
    status: Literal["evaluated", "not_applicable"]


class ScreeningScoreRequest(BaseModel):
    candidate_id: NonEmptyId
    job_id: NonEmptyId
    application_id: int
    criteria_id: int

    category_scores: dict[CategoryName, CategoryScore]

    category_weights: dict[CategoryName, float] = Field(
        min_length=7,
        max_length=7,
    )
    matching_details: dict = Field(default_factory=dict)
    passing_score: float = Field(default=70, ge=0, le=100)

    @model_validator(mode="after")
    def validate_categories_and_weights(self):
        received_categories = set(self.category_scores.keys())

        if received_categories != REQUIRED_CATEGORIES:
            missing = REQUIRED_CATEGORIES - received_categories
            extra = received_categories - REQUIRED_CATEGORIES

            details = []

            if missing:
                details.append(f"missing categories: {sorted(missing)}")

            if extra:
                details.append(f"unexpected categories: {sorted(extra)}")

            raise ValueError("; ".join(details))

        received_weights = set(self.category_weights.keys())

        if received_weights != REQUIRED_CATEGORIES:
            missing = REQUIRED_CATEGORIES - received_weights
            extra = received_weights - REQUIRED_CATEGORIES

            details = []

            if missing:
                details.append(f"missing weights: {sorted(missing)}")

            if extra:
                details.append(f"unexpected weights: {sorted(extra)}")

            raise ValueError("; ".join(details))

        for category_name, weight in self.category_weights.items():
            if weight < 0 or weight > 100:
                raise ValueError(
                    f"weight for {category_name} must be between 0 and 100"
                )

        return self


class CategoryBreakdown(BaseModel):
    score: float | None
    weight: float | None
    weighted_score: float | None
    status: Literal["evaluated", "not_applicable"]


class ScreeningScoreResponse(BaseModel):
    candidate_id: str
    job_id: str
    application_id: int
    criteria_id: int
    category_breakdown: dict[CategoryName, CategoryBreakdown]
    matched_criteria: list[str]
    missing_criteria: list[str]
    matching_details: dict
    overall_score: float
    passing_score: float
    final_status: Literal["recommended", "not_recommended"]


class ScreeningResultSummary(BaseModel):
    application_id: int
    candidate_id: str
    name: str
    overall_score: float
    status: str
    job_title: str


class ScreeningResultDetail(BaseModel):
    application_id: int
    criteria_id: int
    candidate_id: str
    candidate_name: str
    job_id: str
    job_title: str
    overall_score: float
    passing_score: float
    confidence_score: float | None
    final_status: str
    category_breakdown: dict
    matched_criteria: list[str]
    missing_criteria: list[str]
    matching_details: dict