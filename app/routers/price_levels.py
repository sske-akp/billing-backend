from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/price_levels",
    tags=["price_levels"],
)


@router.post("/", response_model=schemas.PriceLevel)
def create_price_level(price_level: schemas.PriceLevelCreate, db: Session = Depends(get_db)):
    db_price_level = models.PriceLevel(**price_level.model_dump())
    db.add(db_price_level)
    db.commit()
    db.refresh(db_price_level)
    return db_price_level


@router.get("/", response_model=List[schemas.PriceLevel])
def read_price_levels(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    price_levels = (
        db.query(models.PriceLevel)
        .order_by(models.PriceLevel.sort_order)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return price_levels


@router.get("/{price_level_id}", response_model=schemas.PriceLevel)
def read_price_level(price_level_id: uuid.UUID, db: Session = Depends(get_db)):
    db_price_level = (
        db.query(models.PriceLevel)
        .filter(models.PriceLevel.id == price_level_id)
        .first()
    )
    if db_price_level is None:
        raise HTTPException(status_code=404, detail="Price level not found")
    return db_price_level


@router.put("/{price_level_id}", response_model=schemas.PriceLevel)
def update_price_level(
    price_level_id: uuid.UUID,
    price_level: schemas.PriceLevelCreate,
    db: Session = Depends(get_db),
):
    db_price_level = (
        db.query(models.PriceLevel)
        .filter(models.PriceLevel.id == price_level_id)
        .first()
    )
    if db_price_level is None:
        raise HTTPException(status_code=404, detail="Price level not found")

    for key, value in price_level.model_dump(exclude_unset=True).items():
        setattr(db_price_level, key, value)

    db.commit()
    db.refresh(db_price_level)
    return db_price_level


@router.delete("/{price_level_id}")
def delete_price_level(price_level_id: uuid.UUID, db: Session = Depends(get_db)):
    db_price_level = (
        db.query(models.PriceLevel)
        .filter(models.PriceLevel.id == price_level_id)
        .first()
    )
    if db_price_level is None:
        raise HTTPException(status_code=404, detail="Price level not found")

    db.delete(db_price_level)
    db.commit()
    return {"detail": "Price level deleted successfully"}
