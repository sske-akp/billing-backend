"""add place_of_supply to invoices

Revision ID: c4a1e8b9d2f3
Revises: b7f3a9c12d45
Create Date: 2026-06-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4a1e8b9d2f3'
down_revision: Union[str, Sequence[str], None] = 'b7f3a9c12d45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('invoices', sa.Column('place_of_supply', sa.String(), nullable=True), schema='sskedata')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('invoices', 'place_of_supply', schema='sskedata')
