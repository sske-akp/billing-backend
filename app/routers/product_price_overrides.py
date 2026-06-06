from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/product_price_overrides",
    tags=["product_price_overrides"],
)


@router.post("/", response_model=schemas.ProductPriceOverride)
def create_product_price_override(
    override: schemas.ProductPriceOverrideCreate,
    db: Session = Depends(get_db),
):
    db_override = models.ProductPriceOverride(**override.model_dump())
    db.add(db_override)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail="A price override for this product and price level already exists",
            )
        raise
    db.refresh(db_override)
    return db_override


@router.get("/", response_model=List[schemas.ProductPriceOverride])
def read_product_price_overrides(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    overrides = (
        db.query(models.ProductPriceOverride)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return overrides


@router.get("/product/{product_id}", response_model=List[schemas.ProductPriceOverride])
def read_overrides_for_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    """Return all price overrides for a given product across all price levels."""
    overrides = (
        db.query(models.ProductPriceOverride)
        .filter(models.ProductPriceOverride.product_id == product_id)
        .all()
    )
    return overrides


@router.get("/{override_id}", response_model=schemas.ProductPriceOverride)
def read_product_price_override(override_id: uuid.UUID, db: Session = Depends(get_db)):
    db_override = (
        db.query(models.ProductPriceOverride)
        .filter(models.ProductPriceOverride.id == override_id)
        .first()
    )
    if db_override is None:
        raise HTTPException(status_code=404, detail="Price override not found")
    return db_override


@router.put("/{override_id}", response_model=schemas.ProductPriceOverride)
def update_product_price_override(
    override_id: uuid.UUID,
    override: schemas.ProductPriceOverrideCreate,
    db: Session = Depends(get_db),
):
    db_override = (
        db.query(models.ProductPriceOverride)
        .filter(models.ProductPriceOverride.id == override_id)
        .first()
    )
    if db_override is None:
        raise HTTPException(status_code=404, detail="Price override not found")

    for key, value in override.model_dump(exclude_unset=True).items():
        setattr(db_override, key, value)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail="A price override for this product and price level already exists",
            )
        raise
    db.refresh(db_override)
    return db_override


@router.delete("/{override_id}")
def delete_product_price_override(override_id: uuid.UUID, db: Session = Depends(get_db)):
    db_override = (
        db.query(models.ProductPriceOverride)
        .filter(models.ProductPriceOverride.id == override_id)
        .first()
    )
    if db_override is None:
        raise HTTPException(status_code=404, detail="Price override not found")

    db.delete(db_override)
    db.commit()
    return {"detail": "Price override deleted successfully"}
