from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CandidateReport(Base):
    """
    Stores the generated report content for a single CandidateEvaluation.

    candidate_id, interview_id, overall_score, and skill_scores are
    intentionally not columns here:
      - overall_score / skill_scores are owned by CandidateEvaluation
        (candidate_evaluation_id -> CandidateEvaluation.overall_score /
        .skill_scores)
      - interview_id is reachable via candidate_evaluation_id ->
        CandidateEvaluation.interview_id.
      - candidate_id is reachable via that interview_id -> Interview
        .application_id -> Application.candidate_id.
    """

    __tablename__ = "candidate_reports"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    candidate_evaluation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("candidate_evaluations.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    strengths: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )

    areas_for_improvement: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )

    recommendation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
