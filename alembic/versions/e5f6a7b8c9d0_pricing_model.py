"""pricing model: price_levels, product_price_overrides, mrp/discount columns

Revision ID: e5f6a7b8c9d0
Revises: c1d2e3f4a5b6
Create Date: 2026-06-07 00:00:00.000000

Adds:
  - price_levels table
  - product_price_overrides table (with unique constraint on product + level)
  - categories.discount_percent (nullable)
  - products.mrp (nullable)
  - products.discount_percent (nullable)
  - customers.price_level_id (nullable FK)
  - customers.state_code (nullable)
  - customers.credit_limit (nullable)
  - customers.payment_terms_days (nullable)
  - customers.disabled (nullable, default False)

All new columns are nullable — safe additive change.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- price_levels table ---------------------------------------------------
    op.create_table(
        'price_levels',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('extra_discount_percent', sa.Numeric(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- product_price_overrides table ----------------------------------------
    op.create_table(
        'product_price_overrides',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('price_level_id', sa.UUID(), nullable=False),
        sa.Column('price', sa.Numeric(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['price_level_id'], ['price_levels.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'price_level_id', name='uq_product_price_level'),
    )

    # --- product_categories: add discount_percent ----------------------------
    op.add_column(
        'product_categories',
        sa.Column('discount_percent', sa.Numeric(), nullable=True),
    )

    # --- products: add mrp and discount_percent -------------------------------
    op.add_column(
        'products',
        sa.Column('mrp', sa.Numeric(), nullable=True),
    )
    op.add_column(
        'products',
        sa.Column('discount_percent', sa.Numeric(), nullable=True),
    )

    # --- customers: add pricing / CRM columns ---------------------------------
    op.add_column(
        'customers',
        sa.Column('price_level_id', sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        'fk_customers_price_level_id',
        'customers',
        'price_levels',
        ['price_level_id'],
        ['id'],
    )
    op.add_column(
        'customers',
        sa.Column('state_code', sa.String(2), nullable=True),
    )
    op.add_column(
        'customers',
        sa.Column('credit_limit', sa.Numeric(), nullable=True),
    )
    op.add_column(
        'customers',
        sa.Column('payment_terms_days', sa.Integer(), nullable=True),
    )
    op.add_column(
        'customers',
        sa.Column('disabled', sa.Boolean(), nullable=True, server_default=sa.false()),
    )


def downgrade() -> None:
    # --- customers: remove added columns -------------------------------------
    op.drop_column('customers', 'disabled')
    op.drop_column('customers', 'payment_terms_days')
    op.drop_column('customers', 'credit_limit')
    op.drop_column('customers', 'state_code')
    op.drop_constraint('fk_customers_price_level_id', 'customers', type_='foreignkey')
    op.drop_column('customers', 'price_level_id')

    # --- products: remove added columns --------------------------------------
    op.drop_column('products', 'discount_percent')
    op.drop_column('products', 'mrp')

    # --- product_categories: remove added column -----------------------------
    op.drop_column('product_categories', 'discount_percent')

    # --- drop new tables (reverse order for FK safety) -----------------------
    op.drop_table('product_price_overrides')
    op.drop_table('price_levels')
