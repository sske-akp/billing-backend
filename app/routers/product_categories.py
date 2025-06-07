from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/product_categories",
    tags=["product_categories"],
)

@router.post("/", response_model=schemas.ProductCategory)
def create_product_category(category: schemas.ProductCategoryCreate, db: Session = Depends(get_db)):
    db_category = models.ProductCategory(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.get("/", response_model=List[schemas.ProductCategory])
def read_product_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    categories = db.query(models.ProductCategory).offset(skip).limit(limit).all()
    return categories

@router.get("/{category_id}", response_model=schemas.ProductCategory)
def read_product_category(category_id: uuid.UUID, db: Session = Depends(get_db)):
    db_category = db.query(models.ProductCategory).filter(models.ProductCategory.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Product Category not found")
    return db_category

@router.put("/{category_id}", response_model=schemas.ProductCategory)
def update_product_category(category_id: uuid.UUID, category: schemas.ProductCategoryCreate, db: Session = Depends(get_db)):
    db_category = db.query(models.ProductCategory).filter(models.ProductCategory.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Product Category not found")

    for key, value in category.model_dump(exclude_unset=True).items():
        setattr(db_category, key, value)

    db.commit()
    db.refresh(db_category)
    return db_category

@router.delete("/{category_id}")
def delete_product_category(category_id: uuid.UUID, db: Session = Depends(get_db)):
    db_category = db.query(models.ProductCategory).filter(models.ProductCategory.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Product Category not found")

    db.delete(db_category)
    db.commit()
    return {"detail": "Product Category deleted successfully"}
