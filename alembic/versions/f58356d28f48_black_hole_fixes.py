"""black_hole_fixes

Revision ID: f58356d28f48
Revises: c2a3b4d5e6f7
Create Date: 2026-03-07 23:47:48.750188

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'f58356d28f48'
down_revision: Union[str, None] = 'c2a3b4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Invoice: add status and reference_invoice_id columns
    op.add_column('invoices', sa.Column('status', sa.String(), server_default='active'), schema='sskedata')
    op.add_column('invoices', sa.Column('reference_invoice_id', UUID(as_uuid=True), nullable=True), schema='sskedata')
    op.create_foreign_key(
        'fk_invoices_reference_invoice_id', 'invoices', 'invoices',
        ['reference_invoice_id'], ['id'],
        source_schema='sskedata', referent_schema='sskedata'
    )

    # Invoice: add unique constraint on invoice_number
    op.create_unique_constraint('uq_invoice_number', 'invoices', ['invoice_number'], schema='sskedata')

    # InvoiceItem: add reference_item_id column
    op.add_column('invoice_items', sa.Column('reference_item_id', UUID(as_uuid=True), nullable=True), schema='sskedata')
    op.create_foreign_key(
        'fk_invoice_items_reference_item_id', 'invoice_items', 'invoice_items',
        ['reference_item_id'], ['id'],
        source_schema='sskedata', referent_schema='sskedata'
    )

    # Product: add gst_rate column
    op.add_column('products', sa.Column('gst_rate', sa.Numeric(), server_default='18'), schema='sskedata')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('products', 'gst_rate', schema='sskedata')

    op.drop_constraint('fk_invoice_items_reference_item_id', 'invoice_items', type_='foreignkey', schema='sskedata')
    op.drop_column('invoice_items', 'reference_item_id', schema='sskedata')

    op.drop_constraint('uq_invoice_number', 'invoices', type_='unique', schema='sskedata')

    op.drop_constraint('fk_invoices_reference_invoice_id', 'invoices', type_='foreignkey', schema='sskedata')
    op.drop_column('invoices', 'reference_invoice_id', schema='sskedata')
    op.drop_column('invoices', 'status', schema='sskedata')
