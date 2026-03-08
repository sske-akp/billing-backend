"""add accounting tables and invoice payment fields

Revision ID: a1b2c3d4e5f6
Revises: f58356d28f48
Create Date: 2026-03-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f58356d28f48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create accounts table (chart of accounts)
    op.create_table(
        'accounts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('account_type', sa.String(), nullable=False),
        sa.Column('parent_id', UUID(as_uuid=True), nullable=True),
        sa.Column('is_system', sa.Boolean(), server_default='true'),
        sa.Column('disabled', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['sskedata.accounts.id'], name='fk_accounts_parent_id'),
        sa.UniqueConstraint('code', name='uq_accounts_code'),
        sa.PrimaryKeyConstraint('id', name='accounts_pkey'),
        schema='sskedata',
    )

    # Create journal_entries table
    op.create_table(
        'journal_entries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('entry_number', sa.String(), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('reference_type', sa.String(), nullable=True),
        sa.Column('reference_id', UUID(as_uuid=True), nullable=True),
        sa.Column('is_auto', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('entry_number', name='uq_journal_entries_entry_number'),
        sa.PrimaryKeyConstraint('id', name='journal_entries_pkey'),
        schema='sskedata',
    )

    # Create journal_lines table
    op.create_table(
        'journal_lines',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('journal_entry_id', UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', UUID(as_uuid=True), nullable=False),
        sa.Column('debit', sa.Numeric(), server_default='0'),
        sa.Column('credit', sa.Numeric(), server_default='0'),
        sa.Column('description', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['journal_entry_id'], ['sskedata.journal_entries.id'], name='fk_journal_lines_entry_id'),
        sa.ForeignKeyConstraint(['account_id'], ['sskedata.accounts.id'], name='fk_journal_lines_account_id'),
        sa.PrimaryKeyConstraint('id', name='journal_lines_pkey'),
        schema='sskedata',
    )

    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('invoice_id', UUID(as_uuid=True), nullable=False),
        sa.Column('customer_id', UUID(as_uuid=True), nullable=True),
        sa.Column('amount', sa.Numeric(), nullable=False),
        sa.Column('payment_method', sa.String(), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('reference_number', sa.String(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('journal_entry_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['sskedata.invoices.id'], name='fk_payments_invoice_id'),
        sa.ForeignKeyConstraint(['customer_id'], ['sskedata.customers.id'], name='fk_payments_customer_id'),
        sa.ForeignKeyConstraint(['journal_entry_id'], ['sskedata.journal_entries.id'], name='fk_payments_journal_entry_id'),
        sa.PrimaryKeyConstraint('id', name='payments_pkey'),
        schema='sskedata',
    )

    # Add payment fields to invoices table
    op.add_column('invoices', sa.Column('payment_status', sa.String(), server_default='unpaid'), schema='sskedata')
    op.add_column('invoices', sa.Column('payment_method', sa.String(), nullable=True), schema='sskedata')
    op.add_column('invoices', sa.Column('due_date', sa.Date(), nullable=True), schema='sskedata')
    op.add_column('invoices', sa.Column('amount_paid', sa.Numeric(), server_default='0'), schema='sskedata')


def downgrade() -> None:
    """Downgrade schema."""
    # Remove payment fields from invoices
    op.drop_column('invoices', 'amount_paid', schema='sskedata')
    op.drop_column('invoices', 'due_date', schema='sskedata')
    op.drop_column('invoices', 'payment_method', schema='sskedata')
    op.drop_column('invoices', 'payment_status', schema='sskedata')

    # Drop tables in reverse dependency order
    op.drop_table('payments', schema='sskedata')
    op.drop_table('journal_lines', schema='sskedata')
    op.drop_table('journal_entries', schema='sskedata')
    op.drop_table('accounts', schema='sskedata')
