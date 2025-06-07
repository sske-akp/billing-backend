from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/product_brands",
    tags=["product_brands"],
)

@router.post("/", response_model=schemas.ProductBrand)
def create_product_brand(brand: schemas.ProductBrandCreate, db: Session = Depends(get_db)):
    db_brand = models.ProductBrand(**brand.model_dump())
    db.add(db_brand)
    db.commit()
    db.refresh(db_brand)
    return db_brand

@router.get("/", response_model=List[schemas.ProductBrand])
def read_product_brands(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    brands = db.query(models.ProductBrand).offset(skip).limit(limit).all()
    return brands

@router.get("/{brand_id}", response_model=schemas.ProductBrand)
def read_product_brand(brand_id: uuid.UUID, db: Session = Depends(get_db)):
    db_brand = db.query(models.ProductBrand).filter(models.ProductBrand.id == brand_id).first()
    if db_brand is None:
        raise HTTPException(status_code=404, detail="Product Brand not found")
    return db_brand

@router.put("/{brand_id}", response_model=schemas.ProductBrand)
def update_product_brand(brand_id: uuid.UUID, brand: schemas.ProductBrandCreate, db: Session = Depends(get_db)):
    db_brand = db.query(models.ProductBrand).filter(models.ProductBrand.id == brand_id).first()
    if db_brand is None:
        raise HTTPException(status_code=404, detail="Product Brand not found")

    for key, value in brand.model_dump(exclude_unset=True).items():
        setattr(db_brand, key, value)

    db.commit()
    db.refresh(db_brand)
    return db_brand

@router.delete("/{brand_id}")
def delete_product_brand(brand_id: uuid.UUID, db: Session = Depends(get_db)):
    db_brand = db.query(models.ProductBrand).filter(models.ProductBrand.id == brand_id).first()
    if db_brand is None:
        raise HTTPException(status_code=404, detail="Product Brand not found")

    db.delete(db_brand)
    db.commit()
    return {"detail": "Product Brand deleted successfully"}
