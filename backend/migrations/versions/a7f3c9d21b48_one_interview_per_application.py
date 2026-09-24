"""enforce one interview per application

Revision ID: a7f3c9d21b48
Revises: 332d1100adc1
Create Date: 2026-09-02

An application should have at most one interview. The service checks for an
existing one before creating, but two concurrent acceptances can both pass
that check and each insert a row, leaving a candidate with two interviews and
no rule about which is theirs.

The existing ("id", "application_id") constraint does not prevent that, since
`id` is the primary key and makes the pair unique for free. It is kept rather
than replaced: candidate_rankings has a composite foreign key pointing at it,
which is what guarantees a ranking's interview and application belong
together. This adds the missing constraint alongside it.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a7f3c9d21b48"
down_revision: Union[str, Sequence[str], None] = "332d1100adc1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT = "uq_interviews_application"


def upgrade() -> None:
    connection = op.get_bind()

    # Fail loudly rather than picking a winner: which interview a candidate
    # keeps is a decision for a person, not a migration.
    duplicates = connection.execute(
        sa.text(
            "SELECT application_id, COUNT(*) AS total "
            "FROM interviews GROUP BY application_id HAVING COUNT(*) > 1"
        )
    ).all()

    if duplicates:
        listed = ", ".join(
            f"application {row.application_id} has {row.total}"
            for row in duplicates
        )

        raise RuntimeError(
            "Cannot enforce one interview per application while duplicates "
            f"exist: {listed}. Remove the extra interviews first."
        )

    op.create_unique_constraint(
        CONSTRAINT, "interviews", ["application_id"]
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT, "interviews", type_="unique")
