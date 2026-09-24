"""create candidate rankings table

Revision ID: c4f21b7e90d3
Revises: 755a962a2c29
Create Date: 2026-08-27 10:12:44.183920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f21b7e90d3'
down_revision: Union[str, Sequence[str], None] = '755a962a2c29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create candidate_rankings table."""
    op.create_unique_constraint(
        "uq_applications_id_job_opportunity",
        "applications",
        ["id", "job_opportunity_id"],
    )

    op.create_unique_constraint(
        "uq_interviews_id_application",
        "interviews",
        ["id", "application_id"],
    )

    op.create_table(
        "candidate_rankings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_opportunity_id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("interview_id", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_opportunity_id"],
            ["job_opportunities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "job_opportunity_id"],
            ["applications.id", "applications.job_opportunity_id"],
            name="fk_candidate_rankings_application_job",
        ),
        sa.ForeignKeyConstraint(
            ["interview_id", "application_id"],
            ["interviews.id", "interviews.application_id"],
            name="fk_candidate_rankings_interview_application",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_opportunity_id",
            "application_id",
            name="uq_candidate_rankings_job_application",
        ),
        sa.UniqueConstraint(
            "job_opportunity_id",
            "rank",
            name="uq_candidate_rankings_job_rank",
        ),
        sa.CheckConstraint(
            "overall_score >= 0 AND overall_score <= 100",
            name="ck_candidate_rankings_overall_score",
        ),
        sa.CheckConstraint(
            "rank >= 1",
            name="ck_candidate_rankings_rank",
        ),
    )

    op.create_index(
        op.f("ix_candidate_rankings_application_id"),
        "candidate_rankings",
        ["application_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_candidate_rankings_interview_id"),
        "candidate_rankings",
        ["interview_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop candidate_rankings table."""
    op.drop_index(
        op.f("ix_candidate_rankings_interview_id"),
        table_name="candidate_rankings",
    )

    op.drop_index(
        op.f("ix_candidate_rankings_application_id"),
        table_name="candidate_rankings",
    )

    op.drop_table("candidate_rankings")

    op.drop_constraint(
        "uq_interviews_id_application",
        "interviews",
        type_="unique",
    )

    op.drop_constraint(
        "uq_applications_id_job_opportunity",
        "applications",
        type_="unique",
    )
