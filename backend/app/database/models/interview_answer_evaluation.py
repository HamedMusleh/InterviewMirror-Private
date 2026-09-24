from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship


from app.database.base import Base


class InterviewAnswerEvaluation(Base):
    __tablename__ = "interview_answer_evaluations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    answer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("interview_answers.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    relevance_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    correctness_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    depth_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    practicality_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    strengths: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    weaknesses: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    answer: Mapped["InterviewAnswer"] = relationship(
        "InterviewAnswer",
        back_populates="evaluation",
    )