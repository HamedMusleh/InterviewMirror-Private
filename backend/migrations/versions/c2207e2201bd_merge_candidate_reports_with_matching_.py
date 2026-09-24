"""merge candidate reports with matching details head

Revision ID: c2207e2201bd
Revises: 78bcb1e79e56, 0195fbb429c3
Create Date: 2026-08-31 17:17:44.729499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2207e2201bd'
down_revision: Union[str, Sequence[str], None] = ('78bcb1e79e56', '0195fbb429c3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
