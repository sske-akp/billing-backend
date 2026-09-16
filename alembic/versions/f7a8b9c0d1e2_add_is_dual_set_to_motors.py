"""add is_dual_set column to motors table

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-06-08 00:00:01.000000

Adds:
  - ``sskedata.motors.is_dual_set``: boolean flag indicating whether the motor model
    tracks separate Pump + Motor (P/M) completeness or is a single-unit model.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "sskedata"


def upgrade() -> None:
    """Add is_dual_set column to motors table."""
    op.execute(
        f"ALTER TABLE {SCHEMA}.motors ADD COLUMN IF NOT EXISTS is_dual_set BOOLEAN NOT NULL DEFAULT TRUE;"
    )


def downgrade() -> None:
    """Drop is_dual_set column from motors table."""
    op.drop_column("motors", "is_dual_set", schema=SCHEMA)
