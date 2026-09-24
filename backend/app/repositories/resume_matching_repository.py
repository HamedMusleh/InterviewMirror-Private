from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.application import Application
from app.database.models.job_opportunity import JobOpportunity
from app.database.models.resume import Resume
from app.database.models.screening_criteria import ScreeningCriteria
from app.schemas.job_description import (
    Experience as JobExperience,
    JobDescriptionResponse,
    Requirements,
    Role,
    ScreeningSettings,
    Skills as JobSkills,
)
from app.schemas.resume import ResumeSchema
from app.schemas.resume_matching import (
    MATCHING_CATEGORY_NAMES,
    MatchingRequest,
)
from app.schemas.screening_criteria import ScreeningCriteria as ScreeningCriteriaSchema


class ResumeMatchingDataError(Exception):
    """Raised when stored matching input cannot be validated."""


class ResumeMatchingNotFoundError(ResumeMatchingDataError):
    """Raised when a required record is missing for an application."""


@dataclass(frozen=True)
class StoredMatchingInput:
    request: MatchingRequest
    application_id: int
    job_opportunity_id: int
    criteria_id: int
    category_weights: dict[str, float]
    passing_score: float


class ResumeMatchingRepository:
    """Loads the persisted records required by the matching pipeline."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def load_for_application(
        self,
        application_id: int,
    ) -> StoredMatchingInput:
        application = self.db.get(Application, application_id)
        if application is None:
            raise ResumeMatchingNotFoundError(
                f"Application {application_id} was not found"
            )

        resume = self.db.scalar(
            select(Resume).where(Resume.application_id == application_id)
        )
        if resume is None:
            raise ResumeMatchingNotFoundError(
                f"Resume for application {application_id} was not found"
            )

        job = self.db.get(JobOpportunity, application.job_opportunity_id)
        if job is None:
            raise ResumeMatchingNotFoundError(
                f"Job opportunity for application {application_id} was not found"
            )

        criteria = self.db.scalar(
            select(ScreeningCriteria).where(
                ScreeningCriteria.job_id == job.id
            )
        )
        if criteria is None:
            raise ResumeMatchingNotFoundError(
                f"Screening criteria for job opportunity {job.id} was not found"
            )

        try:
            criteria_schema = ScreeningCriteriaSchema.model_validate(
                criteria.criteria
            )
            request = MatchingRequest(
                resume=self._resume_schema(resume, application.candidate_id),
                job_description=self._job_description_schema(job),
                screening_criteria=criteria_schema.model_dump(mode="json"),
            )
        except (TypeError, ValidationError) as exc:
            raise ResumeMatchingDataError(
                "Stored resume matching data is invalid"
            ) from exc

        if criteria_schema.job_id != job.job_id:
            raise ResumeMatchingDataError(
                "Stored screening criteria does not belong to the job opportunity"
            )

        category_weights = {
            category_name: float(
                getattr(
                    criteria_schema.screening_criteria,
                    category_name,
                ).weight
            )
            for category_name in MATCHING_CATEGORY_NAMES
        }

        return StoredMatchingInput(
            request=request,
            application_id=application.id,
            job_opportunity_id=job.id,
            criteria_id=criteria.id,
            category_weights=category_weights,
            passing_score=float(criteria_schema.passing_score),
        )

    @staticmethod
    def _resume_schema(
        resume: Resume,
        candidate_id: int,
    ) -> ResumeSchema:
        return ResumeSchema(
            candidate_id=str(candidate_id),
            personal_information=resume.personal_information,
            professional_summary=resume.professional_summary,
            skills=resume.skills,
            experience=resume.experience,
            education=resume.education,
            projects=resume.projects,
            certifications=resume.certifications,
            languages=resume.languages,
        )

    @staticmethod
    def _job_description_schema(job: JobOpportunity) -> JobDescriptionResponse:
        return JobDescriptionResponse(
            job_id=job.job_id,
            role=Role(
                title=job.title,
                department=job.department,
                employment_type=job.employment_type,
                location=job.location,
            ),
            job_summary=job.job_summary,
            responsibilities=job.responsibilities,
            requirements=Requirements(
                skills=JobSkills(
                    required=job.required_skills,
                    preferred=job.preferred_skills,
                ),
                experience=JobExperience(
                    minimum_years=job.minimum_years,
                    level=job.experience_level,
                ),
                education=job.education,
                certifications=job.certifications,
                languages=job.languages,
            ),
            technical_stack=job.technical_stack,
            soft_skills=job.soft_skills,
            screening_settings=ScreeningSettings(
                passing_score=job.passing_score,
            ),
        )
