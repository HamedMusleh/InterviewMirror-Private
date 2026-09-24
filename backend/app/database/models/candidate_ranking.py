from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CandidateRanking(Base):
    """
    A candidate's position in the ranked list of one job opportunity.

    One row represents one application ranked against the other
    applications of the same job opportunity. ``rank`` is 1-based and
    dense: the strongest candidate is rank 1, and ranks are unique
    within a job opportunity.
    """

    __tablename__ = "candidate_rankings"

    __table_args__ = (
        UniqueConstraint(
            "job_opportunity_id",
            "application_id",
            name="uq_candidate_rankings_job_application",
        ),
        UniqueConstraint(
            "job_opportunity_id",
            "rank",
            name="uq_candidate_rankings_job_rank",
        ),
        CheckConstraint(
            "overall_score >= 0 AND overall_score <= 100",
            name="ck_candidate_rankings_overall_score",
        ),
        CheckConstraint(
            "rank >= 1",
            name="ck_candidate_rankings_rank",
        ),
        ForeignKeyConstraint(
            ["application_id", "job_opportunity_id"],
            ["applications.id", "applications.job_opportunity_id"],
            name="fk_candidate_rankings_application_job",
        ),
        ForeignKeyConstraint(
            ["interview_id", "application_id"],
            ["interviews.id", "interviews.application_id"],
            name="fk_candidate_rankings_interview_application",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    job_opportunity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_opportunities.id"),
        nullable=False,
    )

    application_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    interview_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
