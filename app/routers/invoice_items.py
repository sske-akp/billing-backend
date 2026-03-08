from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/invoice_items",
    tags=["invoice_items"],
)

@router.post("/", response_model=schemas.InvoiceItem)
def create_invoice_item(item: schemas.InvoiceItemCreate, db: Session = Depends(get_db)):
    # Decrement batch remaining_qty if batch_id and quantity are provided
    if item.batch_id and item.quantity:
        db_batch = db.query(models.ProductBatch).filter(
            models.ProductBatch.id == item.batch_id
        ).first()
        if db_batch and db_batch.remaining_qty is not None:
            db_batch.remaining_qty -= item.quantity

    db_item = models.InvoiceItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/", response_model=List[schemas.InvoiceItem])
def read_invoice_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = db.query(models.InvoiceItem).offset(skip).limit(limit).all()
    return items

@router.get("/{item_id}", response_model=schemas.InvoiceItem)
def read_invoice_item(item_id: uuid.UUID, db: Session = Depends(get_db)):
    db_item = db.query(models.InvoiceItem).filter(models.InvoiceItem.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Invoice Item not found")
    return db_item

@router.put("/{item_id}", response_model=schemas.InvoiceItem)
def update_invoice_item(item_id: uuid.UUID, item: schemas.InvoiceItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(models.InvoiceItem).filter(models.InvoiceItem.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Invoice Item not found")

    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{item_id}")
def delete_invoice_item(item_id: uuid.UUID, db: Session = Depends(get_db)):
    db_item = db.query(models.InvoiceItem).filter(models.InvoiceItem.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Invoice Item not found")

    # Restore batch remaining_qty when deleting an invoice item
    if db_item.batch_id and db_item.quantity:
        db_batch = db.query(models.ProductBatch).filter(
            models.ProductBatch.id == db_item.batch_id
        ).first()
        if db_batch and db_batch.remaining_qty is not None:
            db_batch.remaining_qty += db_item.quantity

    db.delete(db_item)
    db.commit()
    return {"detail": "Invoice Item deleted successfully"}
