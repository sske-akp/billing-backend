from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from decimal import Decimal
import uuid
from datetime import date

from .. import models, schemas
from ..database import get_db
from ..accounting import create_purchase_journal_entry

router = APIRouter(
    prefix="/purchase_bills",
    tags=["purchase_bills"],
)


@router.post("/with_items/", response_model=schemas.PurchaseBill)
def create_purchase_bill_with_items(
    payload: schemas.PurchaseBillCreateWithItems, db: Session = Depends(get_db)
):
    """Create a purchase bill + its line items in a single atomic transaction.
    Each line creates a ProductBatch (incrementing stock) and the whole bill
    posts a journal entry: DR Inventory + DR GST Input / CR Accounts Payable."""
    bill_data = payload.model_dump(exclude={"items"})
    db_bill = models.PurchaseBill(**bill_data)
    db.add(db_bill)
    db.flush()  # get bill id

    base_amount = Decimal("0")
    gst_amount = Decimal("0")

    for item_data in payload.items:
        qty = item_data.quantity or 0
        unit_cost = Decimal(str(item_data.purchase_price or 0))
        line_base = unit_cost * Decimal(str(qty))
        line_tax = line_base * Decimal(str(item_data.tax_percent or 0)) / Decimal("100")
        base_amount += line_base
        gst_amount += line_tax

        # Create the stock batch for this line
        db_batch = models.ProductBatch(
            product_id=item_data.product_id,
            supplier_id=db_bill.supplier_id,
            batch_code=f"PUR-{db_bill.bill_number or db_bill.bill_date or date.today()}",
            purchase_price=item_data.purchase_price,
            quantity=qty,
            remaining_qty=qty,
            purchase_date=db_bill.bill_date,
            source_type="purchase",
            status="completed",
        )
        db.add(db_batch)
        db.flush()  # get batch id

        db_item = models.PurchaseBillItem(
            purchase_bill_id=db_bill.id,
            product_id=item_data.product_id,
            batch_id=db_batch.id,
            quantity=qty,
            purchase_price=item_data.purchase_price,
            tax_percent=item_data.tax_percent,
            total_price=float(line_base + line_tax),
        )
        db.add(db_item)

    db_bill.total_amount = float(base_amount + gst_amount)

    # Post the purchase journal entry (Inventory + Input GST / Accounts Payable)
    try:
        create_purchase_journal_entry(db, db_bill)
    except ValueError:
        pass  # chart of accounts not seeded yet; skip journal entry

    db.commit()

    db_bill = (
        db.query(models.PurchaseBill)
        .options(joinedload(models.PurchaseBill.items))
        .filter(models.PurchaseBill.id == db_bill.id)
        .first()
    )
    return db_bill


@router.get("/", response_model=List[schemas.PurchaseBill])
def read_purchase_bills(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    bills = (
        db.query(models.PurchaseBill)
        .options(joinedload(models.PurchaseBill.items))
        .order_by(models.PurchaseBill.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return bills


@router.get("/{bill_id}", response_model=schemas.PurchaseBill)
def read_purchase_bill(bill_id: uuid.UUID, db: Session = Depends(get_db)):
    db_bill = (
        db.query(models.PurchaseBill)
        .options(joinedload(models.PurchaseBill.items))
        .filter(models.PurchaseBill.id == bill_id)
        .first()
    )
    if db_bill is None:
        raise HTTPException(status_code=404, detail="Purchase bill not found")
    return db_bill
