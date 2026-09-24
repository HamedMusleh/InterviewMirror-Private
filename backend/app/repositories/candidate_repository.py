from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.candidate import Candidate


class CandidateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        candidate_id: int,
    ) -> Candidate | None:
        statement = select(Candidate).where(
            Candidate.id == candidate_id
        )

        return self.db.scalar(statement)

    def get_by_user_id(
        self,
        user_id: int,
    ) -> Candidate | None:
        statement = select(Candidate).where(
            Candidate.user_id == user_id
        )

        return self.db.scalar(statement)

    def create(
        self,
        user_id: int,
        phone: str | None = None,
    ) -> Candidate:
        """Add a new candidate to the session and flush it.

        Does not commit: candidate creation is one step of the larger
        candidate-resolution flow (see ApplicationService), so the
        caller owns the transaction and commits once every step
        succeeds.
        """

        candidate = Candidate(
            user_id=user_id,
            phone=phone,
        )

        self.db.add(candidate)
        self.db.flush()

        return candidate
