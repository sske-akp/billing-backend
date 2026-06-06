import csv
import io
import uuid as uuid_mod
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db

router = APIRouter(
    prefix="/products",
    tags=["products_csv"],
)


@router.get("/export")
def export_products_csv(db: Session = Depends(get_db)):
    """Export all non-disabled products as a CSV file."""
    products = (
        db.query(models.Product)
        .filter(models.Product.disabled == False)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "hsn_code", "unit", "category", "mrp", "discount_percent", "gst_rate"])

    for p in products:
        category_name = p.category.name if p.category else ""
        writer.writerow([
            str(p.id),
            p.item,
            p.hsncode or "",
            p.unit or "",
            category_name,
            str(p.mrp) if p.mrp is not None else "",
            str(p.discount_percent) if p.discount_percent is not None else "",
            str(p.gst_rate) if p.gst_rate is not None else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products.csv"},
    )


@router.post("/import")
async def import_products_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Import product MRP and discount_percent from a CSV file.
    Updates only existing products by UUID — does not create new products.
    Required CSV columns: id, mrp (optional), discount_percent (optional).
    """
    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    updated = 0
    skipped = 0
    errors: List[str] = []

    for row_num, row in enumerate(reader, start=2):  # start=2 accounting for header row
        raw_id = row.get("id", "").strip()
        if not raw_id:
            skipped += 1
            continue

        try:
            product_id = uuid_mod.UUID(raw_id)
        except ValueError:
            errors.append(f"Row {row_num}: invalid UUID '{raw_id}'")
            skipped += 1
            continue

        db_product = (
            db.query(models.Product)
            .filter(models.Product.id == product_id)
            .first()
        )
        if db_product is None:
            errors.append(f"Row {row_num}: product '{raw_id}' not found")
            skipped += 1
            continue

        changed = False

        raw_mrp = row.get("mrp", "").strip()
        if raw_mrp:
            try:
                db_product.mrp = float(raw_mrp)
                changed = True
            except ValueError:
                errors.append(f"Row {row_num}: invalid mrp value '{raw_mrp}'")

        raw_discount = row.get("discount_percent", "").strip()
        if raw_discount:
            try:
                db_product.discount_percent = float(raw_discount)
                changed = True
            except ValueError:
                errors.append(f"Row {row_num}: invalid discount_percent value '{raw_discount}'")

        if changed:
            updated += 1

    db.commit()
    return {"updated": updated, "skipped": skipped, "errors": errors}
