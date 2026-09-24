from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"),
        nullable=False,
        unique=True,
    )

    criteria_id: Mapped[int] = mapped_column(
        ForeignKey("screening_criteria.id"),
        nullable=False,
    )

    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    matching_details: Mapped[dict] = mapped_column(
    JSONB,
    nullable=True,
    )

    passing_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    final_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    category_breakdown: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    matched_criteria: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    missing_criteria: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )