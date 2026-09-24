from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Interview(Base):
    __tablename__ = "interviews"

    __table_args__ = (
        # Kept because candidate_rankings has a composite foreign key
        # pointing at this pair, which is what guarantees a ranking's
        # interview and application belong together.
        UniqueConstraint(
            "id",
            "application_id",
            name="uq_interviews_id_application",
        ),
        # One interview per application. The service checks before
        # creating, but only the database can stop two concurrent
        # acceptances both inserting a row.
        UniqueConstraint(
            "application_id",
            name="uq_interviews_application",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    application_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("applications.id"),
        nullable=False,
        index=True,
    )

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
