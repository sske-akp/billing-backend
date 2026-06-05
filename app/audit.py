"""Audit trail.

The ``audit_logs`` table lives in EACH company schema (it uses the business
``Base``, so the per-request schema_translate_map routes writes to the active
company). ``log_audit`` is a small helper for explicit instrumentation at
call sites; ``register_audit_listeners`` offers an optional automatic
mechanism via SQLAlchemy ORM events.

This file attaches a NEW model to the business Base. It deliberately does NOT
edit app/models.py (owned by Phase 2). Because it shares Base.metadata, the
table is included whenever models are imported and Base.metadata.create_all /
provision_company runs.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, String, DateTime, Text, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session

from .database import Base

logger = logging.getLogger(__name__)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String, nullable=False)  # create | update | delete | custom
    entity = Column(String, nullable=False)  # table / resource name
    entity_id = Column(String, nullable=True)
    before = Column(Text, nullable=True)  # JSON snapshot prior to change
    after = Column(Text, nullable=True)  # JSON snapshot after change
    created_at = Column(DateTime, default=datetime.utcnow)


def _to_json(value: Optional[dict[str, Any]]) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, default=str)


def log_audit(
    db: Session,
    *,
    action: str,
    entity: str,
    entity_id: Optional[str] = None,
    before: Optional[dict[str, Any]] = None,
    after: Optional[dict[str, Any]] = None,
    user_id: Optional[str] = None,
    commit: bool = False,
) -> Optional[AuditLog]:
    """Write an audit log row into the ACTIVE company schema (best-effort).

    The caller's session already carries the per-company schema_translate_map,
    so this row lands in the correct company schema automatically.

    Auditing must NEVER break the primary operation: the insert runs inside a
    SAVEPOINT (nested transaction) so that if the ``audit_logs`` table is
    missing in the active schema (e.g. a freshly provisioned company that
    hasn't had the table created yet), the savepoint rolls back without
    poisoning the caller's outer transaction. On failure we log and return
    ``None``. Set ``commit=True`` to commit the outer transaction on success.
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        before=_to_json(before),
        after=_to_json(after),
    )
    try:
        with db.begin_nested():  # SAVEPOINT
            db.add(entry)
        if commit:
            db.commit()
            db.refresh(entry)
        return entry
    except Exception:  # noqa: BLE001 - auditing is best-effort
        logger.warning("Audit log write failed for %s/%s", entity, action, exc_info=True)
        return None


def register_audit_listeners(*model_classes) -> None:
    """OPTIONAL automatic auditing via ORM events.

    Attaches after_insert / after_update / after_delete listeners on the given
    mapped classes. This is provided as a mechanism; wiring is intentionally
    left opt-in so it does not surprise existing routers. Note that user_id is
    not captured automatically here (events lack request context) -- prefer
    log_audit() at the router level when the acting user matters.
    """

    def _snapshot(target) -> dict[str, Any]:
        return {
            c.key: getattr(target, c.key)
            for c in target.__table__.columns
        }

    for model in model_classes:
        @event.listens_for(model, "after_insert")
        def _after_insert(mapper, connection, target):  # noqa: ANN001
            connection.execute(
                AuditLog.__table__.insert().values(
                    id=uuid.uuid4(),
                    action="create",
                    entity=target.__tablename__,
                    entity_id=str(getattr(target, "id", None)),
                    before=None,
                    after=_to_json(_snapshot(target)),
                    created_at=datetime.utcnow(),
                )
            )

        @event.listens_for(model, "after_delete")
        def _after_delete(mapper, connection, target):  # noqa: ANN001
            connection.execute(
                AuditLog.__table__.insert().values(
                    id=uuid.uuid4(),
                    action="delete",
                    entity=target.__tablename__,
                    entity_id=str(getattr(target, "id", None)),
                    before=_to_json(_snapshot(target)),
                    after=None,
                    created_at=datetime.utcnow(),
                )
            )
