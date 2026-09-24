from collections.abc import Iterable
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.interview import Interview


class InterviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        interview_id: int,
    ) -> Interview | None:
        statement = select(Interview).where(
            Interview.id == interview_id
        )

        return self.db.scalar(statement)

    def get_by_application_id(
        self,
        application_id: int,
    ) -> Interview | None:
        statement = (
            select(Interview)
            .where(Interview.application_id == application_id)
            .order_by(Interview.id)
        )

        return self.db.scalar(statement)

    def create(
        self,
        application_id: int,
        scheduled_at: datetime,
        status: str,
    ) -> Interview:
        interview = Interview(
            application_id=application_id,
            scheduled_at=scheduled_at,
            status=status,
        )

        self.db.add(interview)
        self.db.flush()
        self.db.refresh(interview)

        return interview

    def update_status(
        self,
        interview_id: int,
        status: str,
    ) -> None:
        interview = self.get_by_id(interview_id)

        if interview is None:
            raise ValueError(f"Interview {interview_id} not found")

        interview.status = status

        self.db.flush()

    def mark_started(
        self,
        interview_id: int,
    ) -> datetime:
        """
        Stamp when the candidate actually began, and return that instant.

        Idempotent on purpose: the candidate reaches this every time they
        open the room, including after a reload, and only the first arrival
        is the start of the interview. Overwriting on each visit would make
        the elapsed clock restart on every refresh, which is the whole
        problem this exists to solve.
        """

        interview = self.get_by_id(interview_id)

        if interview is None:
            raise ValueError(f"Interview {interview_id} not found")

        if interview.started_at is None:
            interview.started_at = datetime.now(timezone.utc)

            self.db.flush()

        return interview.started_at

    def mark_ended(
        self,
        interview_id: int,
    ) -> None:
        """
        Stamp when the interview finished.

        Also idempotent: an interview is completed once, and a re-run of the
        completion path must not move the end of an interview that is already
        over.
        """

        interview = self.get_by_id(interview_id)

        if interview is None:
            raise ValueError(f"Interview {interview_id} not found")

        if interview.ended_at is None:
            interview.ended_at = datetime.now(timezone.utc)

            self.db.flush()

    def get_application_ids_by_ids(
        self,
        interview_ids: Iterable[int],
    ) -> dict[int, int]:
        """
        Map each existing interview id to the application it belongs to.

        Interview ids that do not exist are simply absent from the
        result, so callers can detect them by lookup failure.
        """

        interview_ids = list(interview_ids)

        if not interview_ids:
            return {}

        statement = select(
            Interview.id,
            Interview.application_id,
        ).where(Interview.id.in_(interview_ids))

        return {
            interview_id: application_id
            for interview_id, application_id in self.db.execute(statement)
        }
