"""merge candidate rankings with current head

Revision ID: b849cb658832
Revises: 2c830c26fba2, c4f21b7e90d3
Create Date: 2026-08-29 22:13:37.864093

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b849cb658832'
down_revision: Union[str, Sequence[str], None] = ('2c830c26fba2', 'c4f21b7e90d3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
