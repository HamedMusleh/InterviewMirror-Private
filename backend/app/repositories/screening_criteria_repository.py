from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.screening_criteria import (
    ScreeningCriteria as ScreeningCriteriaModel,
)
from app.schemas.screening_criteria import ScreeningCriteria


class ScreeningCriteriaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_job_opportunity_id(
        self,
        job_opportunity_id: int,
    ) -> ScreeningCriteriaModel | None:
        statement = select(ScreeningCriteriaModel).where(
            ScreeningCriteriaModel.job_id == job_opportunity_id
        )

        return self.db.scalar(statement)

    def delete_for_job_opportunity(
        self,
        job_opportunity_id: int,
    ) -> bool:
        """
        Drop the criteria belonging to a job opportunity.

        Needed on two paths. Deleting a posting would otherwise leave its
        criteria behind pointing at a row that no longer exists, and
        regenerating them after an edit would collide with the unique
        constraint on job_id. Returns whether there was anything to remove,
        so a caller can tell "cleaned up" from "there was nothing there".
        """

        existing = self.get_by_job_opportunity_id(job_opportunity_id)

        if existing is None:
            return False

        try:
            self.db.delete(existing)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return True

    def save(
        self,
        criteria: ScreeningCriteria,
        job_opportunity_id: int,
    ) -> ScreeningCriteriaModel:
        """
        Persist generated ScreeningCriteria for a JobOpportunity.
        """

        now = datetime.now(timezone.utc)

        db_criteria = ScreeningCriteriaModel(
            job_id=job_opportunity_id,
            criteria=criteria.model_dump(),
            created_at=now,
            updated_at=now,
        )

        try:
            self.db.add(db_criteria)
            self.db.commit()
            self.db.refresh(db_criteria)
        except Exception:
            self.db.rollback()
            raise

        return db_criteria