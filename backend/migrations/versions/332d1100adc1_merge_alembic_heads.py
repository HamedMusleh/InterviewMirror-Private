"""merge alembic heads

Revision ID: 332d1100adc1
Revises: 9a1c7f4b2e10, c2207e2201bd
Create Date: 2026-09-02 10:50:20.017949

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '332d1100adc1'
down_revision: Union[str, Sequence[str], None] = ('9a1c7f4b2e10', 'c2207e2201bd')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
