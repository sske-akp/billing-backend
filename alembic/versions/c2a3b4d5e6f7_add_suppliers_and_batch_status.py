"""add suppliers table and batch status

Revision ID: c2a3b4d5e6f7
Revises: b1f2c3d4e5f6
Create Date: 2026-03-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'c2a3b4d5e6f7'
down_revision: Union[str, None] = 'b1f2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create suppliers table
    op.create_table(
        'suppliers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('phone_number', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('gstin', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        schema='sskedata',
    )

    # Add supplier_id and status to product_batches
    op.add_column('product_batches',
        sa.Column('supplier_id', UUID(as_uuid=True), nullable=True),
        schema='sskedata',
    )
    op.add_column('product_batches',
        sa.Column('status', sa.String(), nullable=True, server_default='completed'),
        schema='sskedata',
    )
    op.create_foreign_key(
        'fk_product_batches_supplier_id',
        'product_batches', 'suppliers',
        ['supplier_id'], ['id'],
        source_schema='sskedata',
        referent_schema='sskedata',
    )


def downgrade() -> None:
    op.drop_constraint('fk_product_batches_supplier_id', 'product_batches', schema='sskedata')
    op.drop_column('product_batches', 'status', schema='sskedata')
    op.drop_column('product_batches', 'supplier_id', schema='sskedata')
    op.drop_table('suppliers', schema='sskedata')
