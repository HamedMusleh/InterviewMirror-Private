from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    __table_args__ = (
        UniqueConstraint(
            "interview_id",
            "sequence_number",
            name="uq_interview_questions_interview_sequence",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    interview_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("interviews.id"),
        nullable=False,
    )

    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    question_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    skill: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    is_follow_up: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    parent_question_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("interview_questions.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )