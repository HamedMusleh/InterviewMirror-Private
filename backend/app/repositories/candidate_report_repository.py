from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.candidate_report import (
    CandidateReport as CandidateReportModel,
)
from app.schemas.candidate_report import CandidateReport


class CandidateReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_candidate_evaluation_id(
        self,
        candidate_evaluation_id: int,
    ) -> CandidateReportModel | None:
        statement = select(CandidateReportModel).where(
            CandidateReportModel.candidate_evaluation_id
            == candidate_evaluation_id
        )

        return self.db.scalar(statement)

    def save(
        self,
        report: CandidateReport,
    ) -> CandidateReportModel:

        db_report = CandidateReportModel(
            candidate_evaluation_id=report.candidate_evaluation_id,
            summary=report.summary,
            strengths=report.strengths,
            areas_for_improvement=report.areas_for_improvement,
            recommendation=report.recommendation,
        )

        try:
            self.db.add(db_report)
            self.db.commit()
            self.db.refresh(db_report)
        except Exception:
            self.db.rollback()
            raise

        return db_report

    def list_all(self) -> list[CandidateReportModel]:
        statement = select(CandidateReportModel)

        return list(self.db.scalars(statement).all())