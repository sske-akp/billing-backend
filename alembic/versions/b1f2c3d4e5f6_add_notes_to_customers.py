"""add notes to customers

Revision ID: b1f2c3d4e5f6
Revises: aeebc58faefa
Create Date: 2026-03-06 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1f2c3d4e5f6'
down_revision: Union[str, None] = 'aeebc58faefa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('customers', sa.Column('notes', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('customers', 'notes')
