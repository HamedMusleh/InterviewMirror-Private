from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class QuestionCategory(str, Enum):
    SKILLS = "skills"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    LANGUAGES = "languages"
    SOFT_SKILLS = "soft_skills"


class InterviewQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    category: QuestionCategory
    skill: str | None = None


class QuestionGenerationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[InterviewQuestion]