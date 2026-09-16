from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Optional
import uuid

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/motors",
    tags=["motors"],
)


@router.get("/", response_model=List[schemas.MotorResponse])
def get_motors(
    hp: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Retrieve all motor entries.

    Optionally filter by HP category or search across HP and model name.
    """
    query = db.query(models.Motor)

    if hp:
        query = query.filter(models.Motor.hp == hp)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (models.Motor.hp.ilike(search_pattern))
            | (models.Motor.model.ilike(search_pattern))
        )

    return query.order_by(models.Motor.hp.asc(), models.Motor.model.asc()).all()


@router.get("/{motor_id}", response_model=schemas.MotorResponse)
def get_motor(motor_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retrieve a single motor entry by UUID."""
    motor = db.query(models.Motor).filter(models.Motor.id == motor_id).first()
    if not motor:
        raise HTTPException(status_code=404, detail="Motor not found")
    return motor


@router.post("/", response_model=schemas.MotorResponse)
def create_motor(payload: schemas.MotorCreate, db: Session = Depends(get_db)):
    """Create a new motor entry (HP rating, optional model name, and initial serials)."""
    serials: List[str] = []
    seen = set()
    for s in payload.serials:
        clean = s.strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            serials.append(clean)

    db_motor = models.Motor(
        hp=payload.hp.strip(),
        model=payload.model.strip() if payload.model else None,
        serials=serials,
        is_dual_set=payload.is_dual_set,
    )
    db.add(db_motor)
    db.commit()
    db.refresh(db_motor)
    return db_motor


@router.put("/{motor_id}", response_model=schemas.MotorResponse)
def update_motor(
    motor_id: uuid.UUID,
    payload: schemas.MotorUpdate,
    db: Session = Depends(get_db),
):
    """Update a motor's HP rating, model name, or full serials list."""
    motor = db.query(models.Motor).filter(models.Motor.id == motor_id).first()
    if not motor:
        raise HTTPException(status_code=404, detail="Motor not found")

    if payload.hp is not None:
        motor.hp = payload.hp.strip()
    if payload.model is not None:
        motor.model = payload.model.strip() if payload.model else None
    if payload.serials is not None:
        seen = set()
        cleaned: List[str] = []
        for s in payload.serials:
            clean = s.strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                cleaned.append(clean)
        motor.serials = cleaned
        flag_modified(motor, "serials")
    if payload.is_dual_set is not None:
        motor.is_dual_set = payload.is_dual_set

    db.commit()
    db.refresh(motor)
    return motor


@router.delete("/{motor_id}")
def delete_motor(motor_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a motor model and its serials."""
    motor = db.query(models.Motor).filter(models.Motor.id == motor_id).first()
    if not motor:
        raise HTTPException(status_code=404, detail="Motor not found")

    db.delete(motor)
    db.commit()
    return {"detail": "Motor deleted successfully"}


@router.post("/{motor_id}/serials", response_model=schemas.MotorResponse)
def add_serials_to_motor(
    motor_id: uuid.UUID,
    payload: schemas.MotorSerialsAddBatch,
    db: Session = Depends(get_db),
):
    """Add one or more serial numbers to a motor model."""
    motor = db.query(models.Motor).filter(models.Motor.id == motor_id).first()
    if not motor:
        raise HTTPException(status_code=404, detail="Motor not found")

    current_serials = list(motor.serials or [])
    existing_set = {s.lower() for s in current_serials}

    for s in payload.serials:
        clean = s.strip()
        if clean and clean.lower() not in existing_set:
            existing_set.add(clean.lower())
            current_serials.append(clean)

    motor.serials = current_serials
    flag_modified(motor, "serials")
    db.commit()
    db.refresh(motor)
    return motor


@router.delete(
    "/{motor_id}/serials/{serial_number}",
    response_model=schemas.MotorResponse,
)
def remove_serial_from_motor(
    motor_id: uuid.UUID,
    serial_number: str,
    db: Session = Depends(get_db),
):
    """Remove a single serial number badge from a motor model."""
    motor = db.query(models.Motor).filter(models.Motor.id == motor_id).first()
    if not motor:
        raise HTTPException(status_code=404, detail="Motor not found")

    current_serials = list(motor.serials or [])
    filtered = [s for s in current_serials if s != serial_number]

    motor.serials = filtered
    flag_modified(motor, "serials")
    db.commit()
    db.refresh(motor)
    return motor


@router.put("/hp/{old_hp}", response_model=dict)
def rename_hp_category(
    old_hp: str,
    payload: schemas.MotorHpRename,
    db: Session = Depends(get_db),
):
    """Rename an HP category across all motors having that HP rating."""
    new_hp = payload.new_hp.strip()
    if not new_hp:
        raise HTTPException(status_code=400, detail="New HP name cannot be empty")

    count = (
        db.query(models.Motor)
        .filter(models.Motor.hp == old_hp)
        .update({models.Motor.hp: new_hp}, synchronize_session="fetch")
    )
    db.commit()
    return {
        "detail": f"Renamed {count} records from '{old_hp}' to '{new_hp}'",
        "count": count,
    }


@router.delete("/hp/{hp}", response_model=dict)
def delete_hp_category(hp: str, db: Session = Depends(get_db)):
    """Delete all motors under the specified HP category."""
    count = (
        db.query(models.Motor)
        .filter(models.Motor.hp == hp)
        .delete(synchronize_session="fetch")
    )
    db.commit()
    return {
        "detail": f"Deleted {count} records for HP '{hp}'",
        "count": count,
    }
