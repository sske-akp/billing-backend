"""create motors table for single-table motor and serial tracking

Revision ID: e5f6a7b8c9d0
Revises: c1d2e3f4a5b6
Create Date: 2026-06-08 00:00:00.000000

Creates:
  - ``sskedata.motors`` table: tracks motor HP ratings, model name, and serial numbers.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "sskedata"


def upgrade() -> None:
    """Create the motors table."""
    op.create_table(
        "motors",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("hp", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("serials", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_dual_set", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_sskedata_motors_hp",
        "motors",
        ["hp"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Drop the motors table."""
    op.drop_index("ix_sskedata_motors_hp", table_name="motors", schema=SCHEMA)
    op.drop_table("motors", schema=SCHEMA)
