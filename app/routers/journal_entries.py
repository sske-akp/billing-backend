from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date
from decimal import Decimal
import uuid

from .. import models, schemas
from ..database import get_db
from ..accounting import _generate_entry_number

router = APIRouter(
    prefix="/journal-entries",
    tags=["journal_entries"],
)


@router.get("/", response_model=List[schemas.JournalEntry])
def list_journal_entries(
    skip: int = 0,
    limit: int = 100,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    account_id: Optional[uuid.UUID] = Query(None),
    reference_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(models.JournalEntry).options(
        joinedload(models.JournalEntry.lines)
    )

    if date_from:
        query = query.filter(models.JournalEntry.entry_date >= date_from)
    if date_to:
        query = query.filter(models.JournalEntry.entry_date <= date_to)
    if reference_type:
        query = query.filter(models.JournalEntry.reference_type == reference_type)
    if account_id:
        query = query.join(models.JournalLine).filter(
            models.JournalLine.account_id == account_id
        )

    entries = query.order_by(models.JournalEntry.entry_date.desc()).offset(skip).limit(limit).all()
    return entries


@router.get("/{entry_id}", response_model=schemas.JournalEntry)
def get_journal_entry(entry_id: uuid.UUID, db: Session = Depends(get_db)):
    entry = db.query(models.JournalEntry).options(
        joinedload(models.JournalEntry.lines)
    ).filter(models.JournalEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return entry


@router.post("/", response_model=schemas.JournalEntry)
def create_journal_entry(payload: schemas.JournalEntryCreate, db: Session = Depends(get_db)):
    """Create a manual journal entry. Sum of debits must equal sum of credits."""
    if not payload.lines:
        raise HTTPException(status_code=400, detail="Journal entry must have at least one line")

    total_debit = sum(Decimal(str(line.debit or 0)) for line in payload.lines)
    total_credit = sum(Decimal(str(line.credit or 0)) for line in payload.lines)

    if total_debit != total_credit:
        raise HTTPException(
            status_code=400,
            detail=f"Journal entry does not balance: debit={total_debit}, credit={total_credit}",
        )

    # Validate all account IDs exist
    for line in payload.lines:
        account = db.query(models.Account).filter(models.Account.id == line.account_id).first()
        if not account:
            raise HTTPException(status_code=400, detail=f"Account {line.account_id} not found")

    entry_number = _generate_entry_number(db, payload.entry_date)

    db_entry = models.JournalEntry(
        entry_number=entry_number,
        entry_date=payload.entry_date,
        description=payload.description,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        is_auto=False,
    )
    db.add(db_entry)
    db.flush()

    for line_data in payload.lines:
        db_line = models.JournalLine(
            journal_entry_id=db_entry.id,
            account_id=line_data.account_id,
            debit=Decimal(str(line_data.debit or 0)),
            credit=Decimal(str(line_data.credit or 0)),
            description=line_data.description,
        )
        db.add(db_line)

    db.commit()

    # Re-fetch with lines
    db_entry = db.query(models.JournalEntry).options(
        joinedload(models.JournalEntry.lines)
    ).filter(models.JournalEntry.id == db_entry.id).first()
    return db_entry
