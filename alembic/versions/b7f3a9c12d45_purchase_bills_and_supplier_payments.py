"""purchase bills and supplier payments

Revision ID: b7f3a9c12d45
Revises: d3bc00b81c27
Create Date: 2026-06-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7f3a9c12d45'
down_revision: Union[str, Sequence[str], None] = 'd3bc00b81c27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('purchase_bills',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('bill_number', sa.String(), nullable=True),
    sa.Column('supplier_id', sa.UUID(), nullable=True),
    sa.Column('bill_date', sa.Date(), nullable=True),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('total_amount', sa.Numeric(), nullable=True),
    sa.Column('amount_paid', sa.Numeric(), nullable=True),
    sa.Column('payment_status', sa.String(), nullable=True),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('notes', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['supplier_id'], ['sskedata.suppliers.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='sskedata'
    )
    op.create_index(op.f('ix_sskedata_purchase_bills_bill_number'), 'purchase_bills', ['bill_number'], unique=False, schema='sskedata')
    op.create_table('purchase_bill_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('purchase_bill_id', sa.UUID(), nullable=False),
    sa.Column('product_id', sa.UUID(), nullable=True),
    sa.Column('batch_id', sa.UUID(), nullable=True),
    sa.Column('quantity', sa.Integer(), nullable=True),
    sa.Column('purchase_price', sa.Numeric(), nullable=True),
    sa.Column('tax_percent', sa.Numeric(), nullable=True),
    sa.Column('total_price', sa.Numeric(), nullable=True),
    sa.ForeignKeyConstraint(['batch_id'], ['sskedata.product_batches.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['sskedata.products.id'], ),
    sa.ForeignKeyConstraint(['purchase_bill_id'], ['sskedata.purchase_bills.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='sskedata'
    )

    # Generalize payments: support supplier payouts and on-account receipts
    op.add_column('payments', sa.Column('direction', sa.String(), nullable=True), schema='sskedata')
    op.add_column('payments', sa.Column('supplier_id', sa.UUID(), nullable=True), schema='sskedata')
    op.add_column('payments', sa.Column('purchase_bill_id', sa.UUID(), nullable=True), schema='sskedata')
    op.alter_column('payments', 'invoice_id', existing_type=sa.UUID(), nullable=True, schema='sskedata')
    op.create_foreign_key('fk_payments_supplier_id', 'payments', 'suppliers', ['supplier_id'], ['id'], source_schema='sskedata', referent_schema='sskedata')
    op.create_foreign_key('fk_payments_purchase_bill_id', 'payments', 'purchase_bills', ['purchase_bill_id'], ['id'], source_schema='sskedata', referent_schema='sskedata')
    # Backfill existing rows as customer receipts
    op.execute("UPDATE sskedata.payments SET direction = 'in' WHERE direction IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_payments_purchase_bill_id', 'payments', type_='foreignkey', schema='sskedata')
    op.drop_constraint('fk_payments_supplier_id', 'payments', type_='foreignkey', schema='sskedata')
    op.alter_column('payments', 'invoice_id', existing_type=sa.UUID(), nullable=False, schema='sskedata')
    op.drop_column('payments', 'purchase_bill_id', schema='sskedata')
    op.drop_column('payments', 'supplier_id', schema='sskedata')
    op.drop_column('payments', 'direction', schema='sskedata')
    op.drop_table('purchase_bill_items', schema='sskedata')
    op.drop_index(op.f('ix_sskedata_purchase_bills_bill_number'), table_name='purchase_bills', schema='sskedata')
    op.drop_table('purchase_bills', schema='sskedata')
