from collections.abc import Iterable
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models.application import Application


class ApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        application_id: int,
    ) -> Application | None:
        statement = select(Application).where(
            Application.id == application_id
        )

        return self.db.scalar(statement)

    def get_by_candidate_and_job(
        self,
        candidate_id: int,
        job_opportunity_id: int,
    ) -> Application | None:
        """Find an existing application for this candidate/job pair.

        Used to reject duplicate applications before hitting the
        database-level unique constraint, so callers can surface a
        clear error instead of a raw integrity error.
        """

        statement = select(Application).where(
            Application.candidate_id == candidate_id,
            Application.job_opportunity_id == job_opportunity_id,
        )

        return self.db.scalar(statement)

    def create(
        self,
        candidate_id: int,
        job_opportunity_id: int,
        status: str,
    ) -> Application:
        """Add a new application to the session and flush it.

        Does not commit: application creation and resume persistence
        are one logical operation, so the caller (router/service) owns
        the transaction and commits both together.
        """

        now = datetime.now(timezone.utc)

        application = Application(
            candidate_id=candidate_id,
            job_opportunity_id=job_opportunity_id,
            status=status,
            applied_at=now,
            updated_at=now,
        )

        self.db.add(application)
        self.db.flush()

        return application

    def counts_by_job_opportunity(self) -> dict[int, int]:
        """
        How many applications each posting has, keyed by job opportunity.

        One grouped query rather than a count per card: the job list would
        otherwise issue a query per posting purely to decide whether to
        enable a button.
        """

        statement = (
            select(
                Application.job_opportunity_id,
                func.count(Application.id),
            )
            .group_by(Application.job_opportunity_id)
        )

        return {
            job_opportunity_id: count
            for job_opportunity_id, count in self.db.execute(statement)
        }

    def count_for_job_opportunity(
        self,
        job_opportunity_id: int,
    ) -> int:
        """
        How many candidates have applied to a posting.

        Used to decide whether a posting can be deleted: an application is
        the root of a candidate's resume, screening result, interview and
        answers, so a posting with even one is not something to remove on a
        single click.
        """

        statement = select(func.count()).select_from(Application).where(
            Application.job_opportunity_id == job_opportunity_id
        )

        return self.db.scalar(statement) or 0

    def get_ids_for_job_opportunity(
        self,
        job_opportunity_id: int,
        application_ids: Iterable[int],
    ) -> set[int]:
        """
        Narrow the given application ids to the ones belonging to the job.

        Returns an empty set when no id matches, so callers can treat the
        difference as "not part of this job opportunity".
        """

        application_ids = list(application_ids)

        if not application_ids:
            return set()

        statement = select(Application.id).where(
            Application.job_opportunity_id == job_opportunity_id,
            Application.id.in_(application_ids),
        )

        return set(self.db.scalars(statement).all())
