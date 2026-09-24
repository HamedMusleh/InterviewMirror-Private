from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.job_opportunity import (
    JOB_STATUS_ARCHIVED,
    JobOpportunity,
)
from app.schemas.job_description import JobDescriptionResponse


class JobOpportunityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        job_opportunity_id: int,
    ) -> JobOpportunity | None:
        statement = select(JobOpportunity).where(
            JobOpportunity.id == job_opportunity_id
        )

        return self.db.scalar(statement)

    def get_by_id_for_update(
        self,
        job_opportunity_id: int,
    ) -> JobOpportunity | None:
        """Return and lock a job opportunity until the transaction ends."""

        statement = (
            select(JobOpportunity)
            .where(JobOpportunity.id == job_opportunity_id)
            .with_for_update()
        )

        return self.db.scalar(statement)

    def save(
        self,
        job: JobDescriptionResponse,
        recruiter_id: int,
    ) -> JobOpportunity:
        db_job = JobOpportunity(
            job_id=job.job_id,
            recruiter_id=recruiter_id,
            title=job.role.title,
            department=job.role.department,
            employment_type=job.role.employment_type,
            location=job.role.location,
            job_summary=job.job_summary,
            responsibilities=job.responsibilities,
            required_skills=job.requirements.skills.required,
            preferred_skills=job.requirements.skills.preferred,
            minimum_years=job.requirements.experience.minimum_years,
            experience_level=job.requirements.experience.level,
            education=job.requirements.education,
            certifications=job.requirements.certifications,
            languages=job.requirements.languages,
            technical_stack=job.technical_stack,
            soft_skills=job.soft_skills,
            passing_score=job.screening_settings.passing_score,
            status="draft",
        )

        try:
            self.db.add(db_job)
            self.db.commit()
            self.db.refresh(db_job)
        except Exception:
            self.db.rollback()
            raise

        return db_job

    def get_by_job_id(self, job_id: str) -> JobOpportunity | None:
        return (
            self.db.query(JobOpportunity)
            .filter(JobOpportunity.job_id == job_id)
            .first()
        )

    def update(
        self,
        job_opportunity: JobOpportunity,
        job: JobDescriptionResponse,
    ) -> JobOpportunity:
        """
        Overwrite an existing posting with an edited job description.

        `job_id` and `recruiter_id` are deliberately not touched. The job_id
        is what applications, screening criteria and every link a candidate
        may already hold refer to; reassigning it on an edit would strand
        all of them. Editing changes what the posting says, never which
        posting it is.
        """

        job_opportunity.title = job.role.title
        job_opportunity.department = job.role.department
        job_opportunity.employment_type = job.role.employment_type
        job_opportunity.location = job.role.location
        job_opportunity.job_summary = job.job_summary
        job_opportunity.responsibilities = job.responsibilities
        job_opportunity.required_skills = job.requirements.skills.required
        job_opportunity.preferred_skills = job.requirements.skills.preferred
        job_opportunity.minimum_years = (
            job.requirements.experience.minimum_years
        )
        job_opportunity.experience_level = job.requirements.experience.level
        job_opportunity.education = job.requirements.education
        job_opportunity.certifications = job.requirements.certifications
        job_opportunity.languages = job.requirements.languages
        job_opportunity.technical_stack = job.technical_stack
        job_opportunity.soft_skills = job.soft_skills
        job_opportunity.passing_score = job.screening_settings.passing_score

        try:
            self.db.commit()
            self.db.refresh(job_opportunity)
        except Exception:
            self.db.rollback()
            raise

        return job_opportunity

    def delete(self, job_opportunity: JobOpportunity) -> None:
        """
        Remove a posting.

        The caller is responsible for having established that nothing
        depends on it -- this does not cascade, and the database will refuse
        the delete rather than quietly take candidate data with it.
        """

        try:
            self.db.delete(job_opportunity)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def set_status(
        self,
        job_opportunity: JobOpportunity,
        status: str,
    ) -> JobOpportunity:
        """Move a posting between draft, published and archived."""

        job_opportunity.status = status

        try:
            self.db.commit()
            self.db.refresh(job_opportunity)
        except Exception:
            self.db.rollback()
            raise

        return job_opportunity

    def get_all(
        self,
        include_archived: bool = True,
    ) -> list[JobOpportunity]:
        """
        Every posting, newest first.

        Archived postings are included by default because the recruiter's
        board is the caller that needs them -- closing a job should not
        make it vanish from the person who closed it. The candidate-facing
        list asks for them to be left out.
        """

        statement = select(JobOpportunity)

        if not include_archived:
            statement = statement.where(
                JobOpportunity.status != JOB_STATUS_ARCHIVED
            )

        statement = statement.order_by(JobOpportunity.created_at.desc())

        return list(self.db.scalars(statement).all())
