from sqlalchemy import create_engine, MetaData, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import contextvars
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection URL
DATABASE_URL = os.environ.get('DATABASE_URL')

# Normalize the legacy "postgres://" scheme (still emitted by Neon/Heroku) to
# "postgresql://", which SQLAlchemy 2.x requires.
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create a SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Multi-company support (schema-per-company)
# ---------------------------------------------------------------------------
# The business ``Base`` metadata keeps the logical schema token "sskedata".
# At runtime we DO NOT change the models; instead, every connection checked
# out of the pool gets a ``schema_translate_map`` that rewrites the token
# "sskedata" to the active company's real Postgres schema. The active schema
# is held in a contextvar set per-request by middleware. When unset it
# defaults to "sskedata" so all EXISTING endpoints keep working unchanged
# (i.e. the legacy single-company behaviour is preserved during transition).

# Logical token used by all business models' MetaData (do not change models).
BUSINESS_SCHEMA_TOKEN = "sskedata"
DEFAULT_COMPANY_SCHEMA = "sskedata"

# Per-request active company schema. Defaults to the legacy schema.
_active_company_schema: contextvars.ContextVar[str] = contextvars.ContextVar(
    "active_company_schema", default=DEFAULT_COMPANY_SCHEMA
)


def set_active_company_schema(schema_name: str) -> contextvars.Token:
    """Set the active company schema for the current context.

    Returns the contextvars Token so the caller can reset it afterwards.
    """
    return _active_company_schema.set(schema_name or DEFAULT_COMPANY_SCHEMA)


def reset_active_company_schema(token: contextvars.Token) -> None:
    """Reset the active company schema using a token from set_active_company_schema."""
    _active_company_schema.reset(token)


def get_active_company_schema() -> str:
    """Return the active company schema for the current context."""
    return _active_company_schema.get()


# Create a declarative base object. The token stays "sskedata"; the translate
# map below rewrites it per connection.
Base = declarative_base(metadata=MetaData(schema=BUSINESS_SCHEMA_TOKEN))


@event.listens_for(engine, "engine_connect")
def _apply_schema_translate_map(connection):
    """Apply the per-context schema translate map to each connection.

    Every time a connection is used we rebind the translate map so the
    business token resolves to whatever the active company schema is for the
    current request/context.
    """
    active = get_active_company_schema()
    connection.execution_options(
        schema_translate_map={BUSINESS_SCHEMA_TOKEN: active}
    )


# Dependency to get a database session
def get_db():
    db = SessionLocal()
    # Bind the active schema onto this session's connection explicitly. The
    # engine-level listener handles new connections, but binding here ensures
    # the translate map reflects the contextvar value captured at request time
    # even for pooled connections.
    db.connection(
        execution_options={
            "schema_translate_map": {BUSINESS_SCHEMA_TOKEN: get_active_company_schema()}
        }
    )
    try:
        yield db
    finally:
        db.close()


def provision_company(schema_name: str) -> None:
    """Provision a brand-new company schema.

    1. CREATE SCHEMA IF NOT EXISTS <schema_name>
    2. Create the full set of business tables inside it (via translate map)
    3. Seed the default chart of accounts.

    Importing models/audit/accounting lazily here avoids a circular import at
    module load time (those modules import Base from this module).
    """
    from . import models  # noqa: F401  (ensures all tables are registered on Base)
    from . import audit  # noqa: F401  (registers AuditLog so audit_logs is created too)
    from .accounting import seed_chart_of_accounts

    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))

    # Create all business tables, translating the token to the new schema.
    create_conn = engine.connect().execution_options(
        schema_translate_map={BUSINESS_SCHEMA_TOKEN: schema_name}
    )
    try:
        Base.metadata.create_all(bind=create_conn)
        create_conn.commit()
    finally:
        create_conn.close()

    # Seed the chart of accounts into the new schema.
    token = set_active_company_schema(schema_name)
    db = SessionLocal()
    try:
        db.connection(
            execution_options={
                "schema_translate_map": {BUSINESS_SCHEMA_TOKEN: schema_name}
            }
        )
        seed_chart_of_accounts(db)
    finally:
        db.close()
        reset_active_company_schema(token)


# Import models here so that Base has them before being imported by Alembic
# from . import models
