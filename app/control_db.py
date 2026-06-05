"""Session dependency for the control schema (sske_control).

Control tables live in a FIXED schema and are NOT subject to the per-company
schema_translate_map. We reuse the same engine/SessionLocal but explicitly
clear any translate map on the connection so control queries always resolve
to ``sske_control`` regardless of the active company context.
"""
from sqlalchemy.orm import Session

from .database import SessionLocal


def get_control_db():
    db: Session = SessionLocal()
    # Control models hardcode schema="sske_control" in their metadata, so the
    # business translate map does not affect them. We still ensure no stray
    # translate map leaks in by binding a connection with an empty map.
    db.connection(execution_options={"schema_translate_map": {}})
    try:
        yield db
    finally:
        db.close()
