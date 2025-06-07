from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/invoice_reports",
    tags=["invoice_reports"],
)

@router.get("/invoices/{invoice_id}/items", response_model=List[schemas.InvoiceItem])
def get_invoice_items_for_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db)):
    # Check if the invoice exists
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Get all invoice items for the given invoice_id
    invoice_items = db.query(models.InvoiceItem).filter(models.InvoiceItem.invoice_id == invoice_id).all()

    return invoice_items
