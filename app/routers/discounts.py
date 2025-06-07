from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/discounts",
    tags=["discounts"],
)

@router.post("/", response_model=schemas.Discount)
def create_discount(discount: schemas.DiscountCreate, db: Session = Depends(get_db)):
    db_discount = models.Discount(**discount.model_dump())
    db.add(db_discount)
    db.commit()
    db.refresh(db_discount)
    return db_discount

@router.get("/", response_model=List[schemas.Discount])
def read_discounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    discounts = db.query(models.Discount).offset(skip).limit(limit).all()
    return discounts

@router.get("/{discount_id}", response_model=schemas.Discount)
def read_discount(discount_id: uuid.UUID, db: Session = Depends(get_db)):
    db_discount = db.query(models.Discount).filter(models.Discount.id == discount_id).first()
    if db_discount is None:
        raise HTTPException(status_code=404, detail="Discount not found")
    return db_discount

@router.put("/{discount_id}", response_model=schemas.Discount)
def update_discount(discount_id: uuid.UUID, discount: schemas.DiscountCreate, db: Session = Depends(get_db)):
    db_discount = db.query(models.Discount).filter(models.Discount.id == discount_id).first()
    if db_discount is None:
        raise HTTPException(status_code=404, detail="Discount not found")

    for key, value in discount.model_dump(exclude_unset=True).items():
        setattr(db_discount, key, value)

    db.commit()
    db.refresh(db_discount)
    return db_discount

@router.delete("/{discount_id}")
def delete_discount(discount_id: uuid.UUID, db: Session = Depends(get_db)):
    db_discount = db.query(models.Discount).filter(models.Discount.id == discount_id).first()
    if db_discount is None:
        raise HTTPException(status_code=404, detail="Discount not found")

    db.delete(db_discount)
    db.commit()
    return {"detail": "Discount deleted successfully"}
