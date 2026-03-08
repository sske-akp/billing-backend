from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/accounts",
    tags=["accounts"],
)


@router.get("/", response_model=List[schemas.Account])
def list_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    accounts = db.query(models.Account).filter(
        models.Account.disabled == False
    ).offset(skip).limit(limit).all()
    return accounts


@router.post("/", response_model=schemas.Account)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db)):
    # Check for duplicate code
    existing = db.query(models.Account).filter(models.Account.code == account.code).first()
    if existing:
        raise HTTPException(status_code=409, detail="Account code already exists")

    db_account = models.Account(**account.model_dump())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


@router.put("/{account_id}", response_model=schemas.Account)
def update_account(account_id: uuid.UUID, account: schemas.AccountUpdate, db: Session = Depends(get_db)):
    db_account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if db_account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    for key, value in account.model_dump(exclude_unset=True).items():
        setattr(db_account, key, value)

    db.commit()
    db.refresh(db_account)
    return db_account


@router.delete("/{account_id}")
def delete_account(account_id: uuid.UUID, db: Session = Depends(get_db)):
    db_account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if db_account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    if db_account.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete a system account")

    db_account.disabled = True
    db.commit()
    return {"detail": "Account disabled successfully"}
