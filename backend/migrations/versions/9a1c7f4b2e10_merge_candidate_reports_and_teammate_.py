"""merge candidate_reports and teammate merge heads

Revision ID: 9a1c7f4b2e10
Revises: 0195fbb429c3, 78bcb1e79e56
Create Date: 2026-08-31

Both parents independently merged ('2c830c26fba2', 'c4f21b7e90d3'), which
left the branch with two heads and made `alembic upgrade head` fail. This
is an empty merge revision that rejoins them.
"""

from typing import Sequence, Union


revision: str = "9a1c7f4b2e10"
down_revision: Union[str, Sequence[str], None] = (
    "0195fbb429c3",
    "78bcb1e79e56",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
