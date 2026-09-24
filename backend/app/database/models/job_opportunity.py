from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


# The states a posting can be in.
#
# DRAFT is what every job is created as and, for now, behaves the same as
# published -- candidates can see and apply to it. PUBLISHED exists so that
# distinction can be drawn later without another migration.
#
# ARCHIVED is the one that currently carries weight: the posting stops
# accepting applications and drops off the candidate list, while everything
# already attached to it -- applications, resumes, screening results,
# interviews, recorded answers -- stays exactly where it is. It is the
# answer to "this job is finished" for a posting that cannot be deleted
# precisely because candidates have put work into it.
JOB_STATUS_DRAFT = "draft"
JOB_STATUS_PUBLISHED = "published"
JOB_STATUS_ARCHIVED = "archived"

JOB_STATUSES = (
    JOB_STATUS_DRAFT,
    JOB_STATUS_PUBLISHED,
    JOB_STATUS_ARCHIVED,
)


class JobOpportunity(Base):
    __tablename__ = "job_opportunities"

    __table_args__ = (
        CheckConstraint(
            "passing_score >= 0 AND passing_score <= 100",
            name="ck_job_opportunities_passing_score",
        ),
        CheckConstraint(
            "minimum_years >= 0",
            name="ck_job_opportunities_minimum_years",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    job_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    recruiter_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.id"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    department: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    employment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    location: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    job_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    responsibilities: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    required_skills: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    preferred_skills: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    minimum_years: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    experience_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    education: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    certifications: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    languages: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    technical_stack: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    soft_skills: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    passing_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=70,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def accepting_applications(self) -> bool:
        """
        Whether a candidate may still apply.

        Derived rather than stored so it cannot drift from the status it
        describes. This is the only part of the posting's state that
        reaches candidates; which of draft, published or archived it sits
        in is the recruiter's business.
        """

        return self.status != JOB_STATUS_ARCHIVED