from collections.abc import Sequence

from sqlalchemy import Row, delete, select
from sqlalchemy.orm import Session

from app.database.models.application import Application
from app.database.models.candidate import Candidate
from app.database.models.candidate_ranking import CandidateRanking
from app.database.models.user import User


class CandidateRankingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_ranked_by_job_opportunity_id(
        self,
        job_opportunity_id: int,
    ) -> Sequence[Row]:
        """
        Ranked candidates of a job opportunity, best rank first.

        Each row carries the stored ranking together with the candidate
        identity it belongs to, so the recruiter-facing list needs no
        follow-up lookups.
        """

        statement = (
            select(
                CandidateRanking.rank,
                Application.candidate_id,
                User.first_name,
                User.last_name,
                User.email,
                CandidateRanking.application_id,
                CandidateRanking.interview_id,
                CandidateRanking.overall_score,
                CandidateRanking.created_at,
            )
            .join(
                Application,
                Application.id == CandidateRanking.application_id,
            )
            .join(
                Candidate,
                Candidate.id == Application.candidate_id,
            )
            .join(
                User,
                User.id == Candidate.user_id,
            )
            .where(
                CandidateRanking.job_opportunity_id == job_opportunity_id
            )
            .order_by(CandidateRanking.rank)
        )

        return self.db.execute(statement).all()

    def delete_by_job_opportunity_id(
        self,
        job_opportunity_id: int,
    ) -> None:
        """Remove the stored ranked list of a job opportunity."""

        statement = delete(CandidateRanking).where(
            CandidateRanking.job_opportunity_id == job_opportunity_id
        )

        self.db.execute(statement)

    def create_many(
        self,
        rankings: list[CandidateRanking],
    ) -> list[CandidateRanking]:
        """
        Insert the given rankings and return them with their ids populated.

        The flush is load-bearing: the session is configured with
        ``autoflush=False``, so without it these rows would still be
        pending and the query that reads the stored list back would not
        see them.
        """

        self.db.add_all(rankings)
        self.db.flush()

        return rankings
