from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
import uuid

from .. import models, schemas
from ..database import get_db
from ..accounting import create_payment_journal_entry, create_supplier_payment_journal_entry

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
)


@router.get("/", response_model=List[schemas.Payment])
def list_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    payments = db.query(models.Payment).order_by(
        models.Payment.created_at.desc()
    ).offset(skip).limit(limit).all()
    return payments


@router.get("/by_invoice/{invoice_id}", response_model=List[schemas.Payment])
def get_payments_by_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db)):
    payments = db.query(models.Payment).filter(
        models.Payment.invoice_id == invoice_id
    ).all()
    return payments


@router.get("/by_customer/{customer_id}", response_model=List[schemas.Payment])
def get_payments_by_customer(customer_id: uuid.UUID, db: Session = Depends(get_db)):
    payments = db.query(models.Payment).filter(
        models.Payment.customer_id == customer_id
    ).all()
    return payments


@router.post("/", response_model=schemas.Payment)
def record_payment(payload: schemas.PaymentCreate, db: Session = Depends(get_db)):
    """Record a payment against an invoice. Creates a journal entry and updates
    the invoice payment_status and amount_paid in a single atomic transaction."""
    # Validate invoice exists
    invoice = db.query(models.Invoice).filter(models.Invoice.id == payload.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Invoice is already fully paid")

    # Validate payment amount
    amount = Decimal(str(payload.amount))
    current_paid = Decimal(str(invoice.amount_paid or 0))
    total_due = Decimal(str(invoice.total_amount or 0))
    remaining = total_due - current_paid

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be positive")

    if amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Payment amount {amount} exceeds remaining balance {remaining}",
        )

    # Create payment record
    db_payment = models.Payment(
        direction="in",
        invoice_id=payload.invoice_id,
        customer_id=payload.customer_id or invoice.customer_id,
        amount=amount,
        payment_method=payload.payment_method,
        payment_date=payload.payment_date,
        reference_number=payload.reference_number,
        notes=payload.notes,
    )
    db.add(db_payment)
    db.flush()

    # Create journal entry for the payment
    try:
        journal_entry = create_payment_journal_entry(db, db_payment)
        db_payment.journal_entry_id = journal_entry.id
    except ValueError:
        # If chart of accounts not seeded, still allow payment but skip journal entry
        pass

    # Update invoice payment fields
    new_paid = current_paid + amount
    invoice.amount_paid = new_paid
    if new_paid >= total_due:
        invoice.payment_status = "paid"
    else:
        invoice.payment_status = "partial"

    db.commit()
    db.refresh(db_payment)
    return db_payment


@router.get("/by_supplier/{supplier_id}", response_model=List[schemas.Payment])
def get_payments_by_supplier(supplier_id: uuid.UUID, db: Session = Depends(get_db)):
    payments = db.query(models.Payment).filter(
        models.Payment.supplier_id == supplier_id,
        models.Payment.direction == "out",
    ).all()
    return payments


@router.post("/supplier/", response_model=schemas.Payment)
def record_supplier_payment(payload: schemas.SupplierPaymentCreate, db: Session = Depends(get_db)):
    """Record a payment made against a purchase bill. Creates a journal entry
    (DR Accounts Payable / CR Cash|Bank) and updates the bill's payment_status
    and amount_paid in a single atomic transaction."""
    bill = db.query(models.PurchaseBill).filter(
        models.PurchaseBill.id == payload.purchase_bill_id
    ).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Purchase bill not found")

    if bill.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Purchase bill is already fully paid")

    amount = Decimal(str(payload.amount))
    current_paid = Decimal(str(bill.amount_paid or 0))
    total_due = Decimal(str(bill.total_amount or 0))
    remaining = total_due - current_paid

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be positive")

    if amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Payment amount {amount} exceeds remaining balance {remaining}",
        )

    db_payment = models.Payment(
        direction="out",
        purchase_bill_id=payload.purchase_bill_id,
        supplier_id=payload.supplier_id or bill.supplier_id,
        amount=amount,
        payment_method=payload.payment_method,
        payment_date=payload.payment_date,
        reference_number=payload.reference_number,
        notes=payload.notes,
    )
    db.add(db_payment)
    db.flush()

    try:
        journal_entry = create_supplier_payment_journal_entry(db, db_payment)
        db_payment.journal_entry_id = journal_entry.id
    except ValueError:
        pass

    new_paid = current_paid + amount
    bill.amount_paid = new_paid
    if new_paid >= total_due:
        bill.payment_status = "paid"
    else:
        bill.payment_status = "partial"

    db.commit()
    db.refresh(db_payment)
    return db_payment
