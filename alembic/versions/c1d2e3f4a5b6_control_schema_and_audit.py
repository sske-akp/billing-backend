"""control schema (multi-company, auth, roles) and audit logs

Revision ID: c1d2e3f4a5b6
Revises: c4a1e8b9d2f3
Create Date: 2026-06-04 00:00:00.000000

Creates:
  - the shared ``sske_control`` schema with companies / users / roles /
    user_company_access tables.
  - an ``audit_logs`` table in the default business schema (``sskedata``).
    For additional company schemas, audit_logs is created by
    ``provision_company()`` at runtime, not by this migration.

NOTE: This migration is intentionally NOT auto-generated and is written by
hand because the control tables use a separate metadata that is not wired
into Alembic's autogenerate target.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'c4a1e8b9d2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONTROL_SCHEMA = "sske_control"


def upgrade() -> None:
    """Upgrade schema."""
    # --- Control schema ----------------------------------------------------
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{CONTROL_SCHEMA}"')

    op.create_table(
        'companies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('schema_name', sa.String(), nullable=False),
        sa.Column('gstin', sa.String(), nullable=True),
        sa.Column('state_code', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('schema_name', name='uq_companies_schema_name'),
        schema=CONTROL_SCHEMA,
    )

    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema=CONTROL_SCHEMA,
    )
    op.create_index(
        op.f('ix_sske_control_users_email'),
        'users', ['email'], unique=True, schema=CONTROL_SCHEMA,
    )

    op.create_table(
        'roles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('permissions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_roles_name'),
        schema=CONTROL_SCHEMA,
    )

    op.create_table(
        'user_company_access',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], [f'{CONTROL_SCHEMA}.users.id'], ),
        sa.ForeignKeyConstraint(['company_id'], [f'{CONTROL_SCHEMA}.companies.id'], ),
        sa.ForeignKeyConstraint(['role_id'], [f'{CONTROL_SCHEMA}.roles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'company_id', name='uq_user_company'),
        schema=CONTROL_SCHEMA,
    )

    # --- Audit logs (default business schema) ------------------------------
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('entity', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=True),
        sa.Column('before', sa.Text(), nullable=True),
        sa.Column('after', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='sskedata',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('audit_logs', schema='sskedata')

    op.drop_table('user_company_access', schema=CONTROL_SCHEMA)
    op.drop_table('roles', schema=CONTROL_SCHEMA)
    op.drop_index(
        op.f('ix_sske_control_users_email'),
        table_name='users', schema=CONTROL_SCHEMA,
    )
    op.drop_table('users', schema=CONTROL_SCHEMA)
    op.drop_table('companies', schema=CONTROL_SCHEMA)
    op.execute(f'DROP SCHEMA IF EXISTS "{CONTROL_SCHEMA}"')
