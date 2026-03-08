from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List
import uuid
from datetime import date, datetime

from .. import models, schemas
from ..database import get_db
from ..accounting import create_sale_journal_entry, create_credit_note_journal_entry, create_payment_journal_entry

router = APIRouter(
    prefix="/invoices",
    tags=["invoices"],
)

@router.post("/", response_model=schemas.Invoice)
def create_invoice(invoice: schemas.InvoiceCreate, db: Session = Depends(get_db)):
    db_invoice = models.Invoice(**invoice.model_dump())
    db.add(db_invoice)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        if "uq_invoice_number" in str(e) or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Invoice number already exists")
        raise
    db.refresh(db_invoice)
    return db_invoice

@router.post("/with_items/", response_model=schemas.Invoice)
def create_invoice_with_items(payload: schemas.InvoiceCreateWithItems, db: Session = Depends(get_db)):
    """Create invoice + all items in a single atomic transaction.
    Decrements batch remaining_qty for each item (allows negative/oversell)."""
    # Create the invoice header
    invoice_data = payload.model_dump(exclude={"items"})
    db_invoice = models.Invoice(**invoice_data)
    db.add(db_invoice)
    db.flush()  # Get the invoice ID without committing

    # Create each item and decrement batch stock
    for item_data in payload.items:
        item_dict = item_data.model_dump()
        item_dict["invoice_id"] = db_invoice.id

        # Decrement batch remaining_qty if batch_id and quantity provided
        if item_dict.get("batch_id") and item_dict.get("quantity"):
            db_batch = db.query(models.ProductBatch).filter(
                models.ProductBatch.id == item_dict["batch_id"]
            ).first()
            if db_batch and db_batch.remaining_qty is not None:
                db_batch.remaining_qty -= item_dict["quantity"]

        db_item = models.InvoiceItem(**item_dict)
        db.add(db_item)

    # Create sale journal entry
    try:
        create_sale_journal_entry(db, db_invoice)
    except ValueError:
        pass  # Chart of accounts not seeded yet; skip journal entry

    # If payment_method is provided (immediate payment), create payment + journal entry
    if db_invoice.payment_method in ("cash", "upi", "card"):
        from decimal import Decimal
        total = Decimal(str(db_invoice.total_amount or 0))
        db_payment = models.Payment(
            invoice_id=db_invoice.id,
            customer_id=db_invoice.customer_id,
            amount=total,
            payment_method=db_invoice.payment_method,
            payment_date=db_invoice.invoice_date or date.today(),
        )
        db.add(db_payment)
        db.flush()
        try:
            je = create_payment_journal_entry(db, db_payment)
            db_payment.journal_entry_id = je.id
        except ValueError:
            pass
        db_invoice.amount_paid = total
        db_invoice.payment_status = "paid"

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        if "uq_invoice_number" in str(e) or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Invoice number already exists")
        raise
    # Re-fetch with items loaded
    db_invoice = db.query(models.Invoice).options(
        joinedload(models.Invoice.items)
    ).filter(models.Invoice.id == db_invoice.id).first()
    return db_invoice

@router.post("/credit_note/", response_model=schemas.Invoice)
def create_credit_note(payload: schemas.CreditNoteCreate, db: Session = Depends(get_db)):
    """Create a credit note for an existing invoice, restoring stock."""
    # Fetch the original invoice
    original_invoice = db.query(models.Invoice).options(
        joinedload(models.Invoice.items)
    ).filter(models.Invoice.id == payload.reference_invoice_id).first()

    if not original_invoice:
        raise HTTPException(status_code=404, detail="Original invoice not found")
    if original_invoice.invoice_type != 'sale':
        raise HTTPException(status_code=400, detail="Credit notes can only be created for sale invoices")
    if original_invoice.status == 'cancelled':
        raise HTTPException(status_code=400, detail="Invoice is already cancelled")

    # Build a lookup of original items
    original_items_map = {item.id: item for item in original_invoice.items}

    # Validate each return item
    credit_total = 0
    items_to_create = []

    for cn_item in payload.items:
        original_item = original_items_map.get(cn_item.reference_item_id)
        if not original_item:
            raise HTTPException(
                status_code=400,
                detail=f"Item {cn_item.reference_item_id} not found in original invoice"
            )

        # Calculate already returned quantity for this item
        already_returned = db.query(func.coalesce(func.sum(models.InvoiceItem.quantity), 0)).join(
            models.Invoice, models.InvoiceItem.invoice_id == models.Invoice.id
        ).filter(
            models.InvoiceItem.reference_item_id == cn_item.reference_item_id,
            models.Invoice.invoice_type == 'credit_note'
        ).scalar()

        max_returnable = original_item.quantity - int(already_returned)
        if cn_item.quantity > max_returnable:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot return {cn_item.quantity} units for item {cn_item.reference_item_id}. "
                       f"Max returnable: {max_returnable} (original: {original_item.quantity}, already returned: {int(already_returned)})"
            )

        # Calculate line total for this credit note item
        line_total = float(original_item.selling_price or 0) * cn_item.quantity
        tax_amount = line_total * float(original_item.tax_percent or 0) / 100
        item_total = line_total + tax_amount

        items_to_create.append({
            "product_id": original_item.product_id,
            "batch_id": original_item.batch_id,
            "quantity": cn_item.quantity,
            "selling_price": original_item.selling_price,
            "tax_percent": original_item.tax_percent,
            "total_price": -item_total,
            "is_official": original_item.is_official,
            "reference_item_id": cn_item.reference_item_id,
        })
        credit_total += item_total

    # Generate credit note number
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S%f")
    cn_number = f"CN-{timestamp[:21]}"

    # Create the credit note invoice
    db_credit_note = models.Invoice(
        invoice_number=cn_number,
        customer_id=original_invoice.customer_id,
        invoice_date=date.today(),
        invoice_type='credit_note',
        total_amount=-credit_total,
        status='active',
        reference_invoice_id=payload.reference_invoice_id,
    )
    db.add(db_credit_note)
    db.flush()

    # Create credit note items and restore stock
    for item_data in items_to_create:
        item_data["invoice_id"] = db_credit_note.id
        db_item = models.InvoiceItem(**item_data)
        db.add(db_item)

        # Restore stock on the batch
        if item_data.get("batch_id") and item_data.get("quantity"):
            db_batch = db.query(models.ProductBatch).filter(
                models.ProductBatch.id == item_data["batch_id"]
            ).first()
            if db_batch and db_batch.remaining_qty is not None:
                db_batch.remaining_qty += item_data["quantity"]

    # Create credit note journal entry
    try:
        create_credit_note_journal_entry(db, db_credit_note)
    except ValueError:
        pass  # Chart of accounts not seeded yet; skip journal entry

    # Check if ALL original items are now fully returned
    all_fully_returned = True
    for orig_item in original_invoice.items:
        total_returned = db.query(func.coalesce(func.sum(models.InvoiceItem.quantity), 0)).join(
            models.Invoice, models.InvoiceItem.invoice_id == models.Invoice.id
        ).filter(
            models.InvoiceItem.reference_item_id == orig_item.id,
            models.Invoice.invoice_type == 'credit_note'
        ).scalar()
        if int(total_returned) < orig_item.quantity:
            all_fully_returned = False
            break

    if all_fully_returned:
        original_invoice.status = 'cancelled'

    db.commit()

    # Re-fetch with items loaded
    db_credit_note = db.query(models.Invoice).options(
        joinedload(models.Invoice.items)
    ).filter(models.Invoice.id == db_credit_note.id).first()
    return db_credit_note

@router.get("/", response_model=List[schemas.Invoice])
def read_invoices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    invoices = db.query(models.Invoice).options(joinedload(models.Invoice.items)).offset(skip).limit(limit).all()
    return invoices

@router.get("/{invoice_id}", response_model=schemas.Invoice)
def read_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db)):
    db_invoice = db.query(models.Invoice).options(joinedload(models.Invoice.items)).filter(models.Invoice.id == invoice_id).first()
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db_invoice

@router.put("/{invoice_id}", response_model=schemas.Invoice)
def update_invoice(invoice_id: uuid.UUID, invoice: schemas.InvoiceCreate, db: Session = Depends(get_db)):
    db_invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    for key, value in invoice.model_dump(exclude_unset=True).items():
        setattr(db_invoice, key, value)

    db.commit()
    db.refresh(db_invoice)
    return db_invoice

@router.put("/{invoice_id}/with_items/", response_model=schemas.Invoice)
def update_invoice_with_items(invoice_id: uuid.UUID, payload: schemas.InvoiceCreateWithItems, db: Session = Depends(get_db)):
    """Update invoice header and items, adjusting stock diffs."""
    db_invoice = db.query(models.Invoice).options(
        joinedload(models.Invoice.items)
    ).filter(models.Invoice.id == invoice_id).first()

    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if db_invoice.status != 'active':
        raise HTTPException(status_code=400, detail="Cannot edit a non-active invoice")

    # Check if invoice has credit notes against it
    has_credit_notes = db.query(models.Invoice).filter(
        models.Invoice.reference_invoice_id == invoice_id,
        models.Invoice.invoice_type == 'credit_note'
    ).first()
    if has_credit_notes:
        raise HTTPException(status_code=400, detail="Cannot edit an invoice that has credit notes")

    # Build map of old items by ID
    old_items_map = {item.id: item for item in db_invoice.items}

    # Track which old items are still present (by matching batch_id + product_id)
    new_items_data = [item.model_dump() for item in payload.items]

    # Restore stock for ALL old items first
    for old_item in db_invoice.items:
        if old_item.batch_id and old_item.quantity:
            db_batch = db.query(models.ProductBatch).filter(
                models.ProductBatch.id == old_item.batch_id
            ).first()
            if db_batch and db_batch.remaining_qty is not None:
                db_batch.remaining_qty += old_item.quantity
        db.delete(old_item)

    db.flush()

    # Create new items and decrement stock
    for item_data in new_items_data:
        item_data["invoice_id"] = db_invoice.id
        # Remove id if present (new items)
        item_data.pop("id", None)

        if item_data.get("batch_id") and item_data.get("quantity"):
            db_batch = db.query(models.ProductBatch).filter(
                models.ProductBatch.id == item_data["batch_id"]
            ).first()
            if db_batch and db_batch.remaining_qty is not None:
                db_batch.remaining_qty -= item_data["quantity"]

        db_item = models.InvoiceItem(**item_data)
        db.add(db_item)

    # Update header fields
    header_data = payload.model_dump(exclude={"items"})
    for key, value in header_data.items():
        setattr(db_invoice, key, value)

    db.commit()

    # Re-fetch with items loaded
    db_invoice = db.query(models.Invoice).options(
        joinedload(models.Invoice.items)
    ).filter(models.Invoice.id == invoice_id).first()
    return db_invoice

@router.delete("/{invoice_id}")
def delete_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db)):
    raise HTTPException(
        status_code=405,
        detail="Invoice deletion is not allowed. Use credit notes to cancel invoices."
    )
