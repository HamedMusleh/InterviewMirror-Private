from pydantic import Field
from typing import List

from .base import StrictBaseModel


class SkillWeight(StrictBaseModel):
    name: str
    weight: float = 0


class SkillsCriteria(StrictBaseModel):
    weight: float
    required: List[SkillWeight] = Field(default_factory=list)
    preferred: List[SkillWeight] = Field(default_factory=list)


class ExperienceCriteria(StrictBaseModel):
    weight: float
    minimum_years: int = 0
    level: str = ""


class EducationCriteria(StrictBaseModel):
    weight: float
    preferred_fields: List[str] = Field(default_factory=list)


class ProjectsCriteria(StrictBaseModel):
    weight: float
    required: bool = False
    relevant_domains: List[str] = Field(default_factory=list)


class CertificationsCriteria(StrictBaseModel):
    weight: float
    criteria: List[str] = Field(default_factory=list)


class LanguagesCriteria(StrictBaseModel):
    weight: float
    criteria: List[str] = Field(default_factory=list)


class SoftSkillsCriteria(StrictBaseModel):
    weight: float
    criteria: List[str] = Field(default_factory=list)


class ScreeningCriteriaBody(StrictBaseModel):
    skills: SkillsCriteria
    experience: ExperienceCriteria
    education: EducationCriteria
    projects: ProjectsCriteria
    certifications: CertificationsCriteria
    languages: LanguagesCriteria
    soft_skills: SoftSkillsCriteria


class ScreeningCriteria(StrictBaseModel):
    """
    Final Screening Criteria JSON returned by the LLM,
    to be consumed by the Resume Matching & Scoring module.
    """
    job_id: str
    screening_criteria: ScreeningCriteriaBody
    passing_score: int = 70
