from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"
    __table_args__ = (
        CheckConstraint(
            "answer_text IS NOT NULL OR audio_url IS NOT NULL "
            "OR video_url IS NOT NULL OR transcript IS NOT NULL",
            name="ck_interview_answers_has_content",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("interview_questions.id"),
        nullable=False,
        index=True,
    )

    answer_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    audio_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    video_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    transcript: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    evaluation: Mapped["InterviewAnswerEvaluation | None"] = relationship(
        "InterviewAnswerEvaluation",
        back_populates="answer",
        uselist=False,
    )