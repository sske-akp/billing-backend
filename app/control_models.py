"""Control-schema models for multi-company, auth and access control.

These live in a DEDICATED Postgres schema (``sske_control``) that is shared
across all companies. They use their own declarative ``Base`` so that the
business ``Base`` in :mod:`app.database` (which is subject to the per-request
``schema_translate_map``) is never affected by these tables.

NOTE: this Base must NOT be registered with the business metadata. Alembic's
``target_metadata`` currently points at the business ``Base`` only, so the
control tables are created via an explicit migration (see
``alembic/versions/...control_schema...``) rather than autogenerate.
"""
from datetime import datetime
import uuid

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    MetaData,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

CONTROL_SCHEMA = "sske_control"

# A standalone metadata/Base pinned to the control schema. This is a real,
# fixed schema (NOT a translate-map token) so control data is always resolved
# to the same place regardless of the active company.
ControlBase = declarative_base(metadata=MetaData(schema=CONTROL_SCHEMA))


class Company(ControlBase):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    # Postgres schema that holds this company's business tables.
    schema_name = Column(String, nullable=False, unique=True)
    gstin = Column(String, nullable=True)
    state_code = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    accesses = relationship("UserCompanyAccess", back_populates="company")


class User(ControlBase):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    accesses = relationship("UserCompanyAccess", back_populates="user")


class Role(ControlBase):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    # JSON-encoded list of permission strings (stored as TEXT for portability).
    permissions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    accesses = relationship("UserCompanyAccess", back_populates="role")


class UserCompanyAccess(ControlBase):
    __tablename__ = "user_company_access"
    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_user_company"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey(f"{CONTROL_SCHEMA}.users.id"),
        nullable=False,
    )
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey(f"{CONTROL_SCHEMA}.companies.id"),
        nullable=False,
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey(f"{CONTROL_SCHEMA}.roles.id"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="accesses")
    company = relationship("Company", back_populates="accesses")
    role = relationship("Role", back_populates="accesses")
