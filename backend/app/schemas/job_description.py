from typing import Annotated, List, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class ScreeningSettings(BaseModel):
    passing_score: int = Field(
        default=70,
        ge=0,
        le=100,
        description="Minimum screening score required to pass",
    )


class Role(BaseModel):
    title: NonEmptyString
    department: NonEmptyString
    employment_type: NonEmptyString
    location: NonEmptyString


class Skills(BaseModel):
    required: List[NonEmptyString] = Field(default_factory=list)
    preferred: List[NonEmptyString] = Field(default_factory=list)


class Experience(BaseModel):
    minimum_years: int = Field(default=0, ge=0)
    level: NonEmptyString


class Requirements(BaseModel):
    skills: Skills
    experience: Experience
    education: List[NonEmptyString] = Field(default_factory=list)
    certifications: List[NonEmptyString] = Field(default_factory=list)
    languages: List[NonEmptyString] = Field(default_factory=list)


class JobDescription(BaseModel):
    role: Role
    job_summary: NonEmptyString
    responsibilities: List[NonEmptyString] = Field(default_factory=list)
    requirements: Requirements
    technical_stack: List[NonEmptyString] = Field(default_factory=list)
    soft_skills: List[NonEmptyString] = Field(default_factory=list)
    screening_settings: ScreeningSettings = Field(
        default_factory=ScreeningSettings
    )


class JobDescriptionRequest(BaseModel):
    role: Role
    job_summary: NonEmptyString
    responsibilities: List[NonEmptyString] = Field(default_factory=list)
    requirements: Requirements
    technical_stack: List[NonEmptyString] = Field(default_factory=list)
    soft_skills: List[NonEmptyString] = Field(default_factory=list)
    screening_settings: ScreeningSettings = Field(
        default_factory=ScreeningSettings
    )


class JobDescriptionResponse(BaseModel):
    job_id: str
    role: Role
    job_summary: str
    responsibilities: List[str]
    requirements: Requirements
    technical_stack: List[str]
    soft_skills: List[str]
    screening_settings: ScreeningSettings

class JobStatusUpdateRequest(BaseModel):
    """
    A move between the states a posting can be in.

    Any state may follow any other. Reopening an archived job is a normal
    correction -- a recruiter who closes the wrong posting should be able
    to undo it in one click rather than rebuild it -- so this deliberately
    does not encode a one-way lifecycle.
    """

    status: Literal["draft", "published", "archived"]


class JobOpportunityEditResponse(BaseModel):
    """
    Everything the edit form needs to load a posting back into itself.

    Distinct from JobOpportunityResponse, which is candidate-facing and
    deliberately withholds the screening threshold. An edit form that could
    not read passing_score would have to guess at it, and saving would
    silently reset a recruiter's threshold to the default every time they
    corrected a typo.
    """

    model_config = ConfigDict(from_attributes=True)

    job_id: str
    title: str
    department: str
    employment_type: str
    location: str
    job_summary: str
    responsibilities: List[str]
    required_skills: List[str]
    preferred_skills: List[str]
    minimum_years: int
    experience_level: str
    education: List[str]
    certifications: List[str]
    languages: List[str]
    technical_stack: List[str]
    soft_skills: List[str]
    passing_score: int
    status: str


class JobOpportunitySummaryResponse(BaseModel):
    # How many candidates have applied.
    #
    # Carried so the job list can tell a recruiter that a posting cannot be
    # deleted before they press the button, rather than after. A delete
    # that is refused on submit reads as a broken button; one that is
    # visibly unavailable, with the count as the reason, reads as a rule.
    application_count: int = 0

    job_id: str
    title: str
    department: str
    employment_type: str
    location: str
    job_summary: str
    required_skills: List[str]
    minimum_years: int
    experience_level: str
    status: str
