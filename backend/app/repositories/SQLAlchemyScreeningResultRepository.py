from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.application import Application
from app.database.models.candidate import Candidate
from app.database.models.job_opportunity import JobOpportunity
from app.database.models.screening_result import ScreeningResult
from app.database.models.user import User
from app.handlers.screening_result_handler import ScreeningResultHandler
from app.schemas.screening_score import (
    ScreeningResultDetail,
    ScreeningResultSummary,
    ScreeningScoreResponse,
)


class SQLAlchemyScreeningResultRepository:
    def __init__(self, db: Session, handler: ScreeningResultHandler):
        self.db = db
        self.handler = handler

    def save(self, result: ScreeningScoreResponse) -> ScreeningResult:
        db_result = self.handler.to_db_model(result)

        try:
            self.db.add(db_result)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return db_result

    def list_by_job_id(self, job_id: str) -> list[ScreeningResultSummary]:
        rows = self.db.execute(
            select(ScreeningResult, Candidate, User, JobOpportunity)
            .join(Application, ScreeningResult.application_id == Application.id)
            .join(Candidate, Application.candidate_id == Candidate.id)
            .join(User, Candidate.user_id == User.id)
            .join(
                JobOpportunity,
                Application.job_opportunity_id == JobOpportunity.id,
            )
            .where(JobOpportunity.job_id == job_id)
        ).all()

        return [
            ScreeningResultSummary(
                application_id=screening_result.application_id,
                candidate_id=str(candidate.id),
                name=f"{user.first_name} {user.last_name}",
                overall_score=screening_result.overall_score,
                status=screening_result.final_status,
                job_title=job.title,
            )
            for screening_result, candidate, user, job in rows
        ]

    def get_by_application_id(
        self, application_id: int
    ) -> ScreeningResultDetail | None:
        row = self.db.execute(
            select(ScreeningResult, Candidate, User, JobOpportunity)
            .join(Application, ScreeningResult.application_id == Application.id)
            .join(Candidate, Application.candidate_id == Candidate.id)
            .join(User, Candidate.user_id == User.id)
            .join(
                JobOpportunity,
                Application.job_opportunity_id == JobOpportunity.id,
            )
            .where(ScreeningResult.application_id == application_id)
        ).first()

        if row is None:
            return None

        screening_result, candidate, user, job = row

        return ScreeningResultDetail(
            application_id=screening_result.application_id,
            criteria_id=screening_result.criteria_id,
            candidate_id=str(candidate.id),
            candidate_name=f"{user.first_name} {user.last_name}",
            job_id=job.job_id,
            job_title=job.title,
            overall_score=screening_result.overall_score,
            passing_score=screening_result.passing_score,
            confidence_score=screening_result.confidence_score,
            final_status=screening_result.final_status,
            category_breakdown=screening_result.category_breakdown,
            matched_criteria=screening_result.matched_criteria,
            missing_criteria=screening_result.missing_criteria,
            matching_details=screening_result.matching_details or {}, # for old records that don't have matching_details, return an empty dict
        )