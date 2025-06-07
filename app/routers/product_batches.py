from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/product_batches",
    tags=["product_batches"],
)

@router.post("/", response_model=schemas.ProductBatch)
def create_product_batch(batch: schemas.ProductBatchCreate, db: Session = Depends(get_db)):
    db_batch = models.ProductBatch(**batch.model_dump())
    db.add(db_batch)
    db.commit()
    db.refresh(db_batch)
    return db_batch

@router.get("/", response_model=List[schemas.ProductBatch])
def read_product_batches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    batches = db.query(models.ProductBatch).offset(skip).limit(limit).all()
    return batches

@router.get("/{batch_id}", response_model=schemas.ProductBatch)
def read_product_batch(batch_id: uuid.UUID, db: Session = Depends(get_db)):
    db_batch = db.query(models.ProductBatch).filter(models.ProductBatch.id == batch_id).first()
    if db_batch is None:
        raise HTTPException(status_code=404, detail="Product Batch not found")
    return db_batch

@router.put("/{batch_id}", response_model=schemas.ProductBatch)
def update_product_batch(batch_id: uuid.UUID, batch: schemas.ProductBatchCreate, db: Session = Depends(get_db)):
    db_batch = db.query(models.ProductBatch).filter(models.ProductBatch.id == batch_id).first()
    if db_batch is None:
        raise HTTPException(status_code=404, detail="Product Batch not found")

    for key, value in batch.model_dump(exclude_unset=True).items():
        setattr(db_batch, key, value)

    db.commit()
    db.refresh(db_batch)
    return db_batch

@router.delete("/{batch_id}")
def delete_product_batch(batch_id: uuid.UUID, db: Session = Depends(get_db)):
    db_batch = db.query(models.ProductBatch).filter(models.ProductBatch.id == batch_id).first()
    if db_batch is None:
        raise HTTPException(status_code=404, detail="Product Batch not found")

    db.delete(db_batch)
    db.commit()
    return {"detail": "Product Batch deleted successfully"}
