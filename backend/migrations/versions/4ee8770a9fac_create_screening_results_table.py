"""create screening results table

Revision ID: 4ee8770a9fac
Revises:
Create Date: 2026-08-05 14:27:07.900030

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ee8770a9fac'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create screening_results table."""
    op.create_table(
        "screening_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column(
            "category_breakdown",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("passing_score", sa.Float(), nullable=False),
        sa.Column("final_status", sa.String(), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_screening_results_candidate_id"),
        "screening_results",
        ["candidate_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_screening_results_job_id"),
        "screening_results",
        ["job_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop screening_results table."""
    op.drop_index(
        op.f("ix_screening_results_job_id"),
        table_name="screening_results",
    )

    op.drop_index(
        op.f("ix_screening_results_candidate_id"),
        table_name="screening_results",
    )

    op.drop_table("screening_results")