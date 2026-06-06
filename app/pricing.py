from decimal import Decimal
from typing import Optional

from . import models
from sqlalchemy.orm import Session


def resolve_price(
    db: Session,
    product: models.Product,
    price_level: Optional[models.PriceLevel] = None,
) -> Optional[Decimal]:
    """
    Returns the effective selling price for a product given a customer's price level.

    Resolution order:
    1. Explicit ProductPriceOverride for (product, level) → use it directly
    2. Formula: MRP × (1 - product_discount%) × (1 - level_extra%)
       where product_discount = product.discount_percent ?? category.discount_percent ?? 0
    3. No MRP set → return None (staff enters price manually)
    """
    if price_level:
        override = (
            db.query(models.ProductPriceOverride)
            .filter_by(product_id=product.id, price_level_id=price_level.id)
            .first()
        )
        if override:
            return Decimal(str(override.price))

    if product.mrp is None:
        return None

    product_discount = product.discount_percent
    if product_discount is None and product.category:
        product_discount = product.category.discount_percent
    product_discount = Decimal(str(product_discount)) if product_discount is not None else Decimal(0)

    mrp = Decimal(str(product.mrp))
    base = mrp * (1 - product_discount / 100)

    if price_level and price_level.extra_discount_percent:
        level_discount = Decimal(str(price_level.extra_discount_percent))
        base = base * (1 - level_discount / 100)

    return base.quantize(Decimal("0.01"))
