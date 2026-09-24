"""merge evaluations and matching_details heads

Revision ID: 2c830c26fba2
Revises: dd15c0aef907, dd87f84c84a9
Create Date: 2026-08-29 17:17:22.513422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c830c26fba2'
down_revision: Union[str, Sequence[str], None] = ('dd15c0aef907', 'dd87f84c84a9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
