from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_
from datetime import date, timedelta

from .. import models
from ..database import get_db

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
)

@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    thirty_days_ago = today - timedelta(days=30)

    # Base filter for active sale invoices
    sale_filter = and_(
        models.Invoice.invoice_type == 'sale',
        models.Invoice.status == 'active'
    )

    # Sales metrics
    total_revenue = db.query(
        func.coalesce(func.sum(models.Invoice.total_amount), 0)
    ).filter(sale_filter).scalar()

    invoice_count = db.query(
        func.count(models.Invoice.id)
    ).filter(sale_filter).scalar()

    revenue_today = db.query(
        func.coalesce(func.sum(models.Invoice.total_amount), 0)
    ).filter(sale_filter, models.Invoice.invoice_date == today).scalar()

    revenue_this_week = db.query(
        func.coalesce(func.sum(models.Invoice.total_amount), 0)
    ).filter(sale_filter, models.Invoice.invoice_date >= start_of_week).scalar()

    revenue_this_month = db.query(
        func.coalesce(func.sum(models.Invoice.total_amount), 0)
    ).filter(sale_filter, models.Invoice.invoice_date >= start_of_month).scalar()

    sales_metrics = {
        "total_revenue": float(total_revenue),
        "invoice_count": int(invoice_count),
        "revenue_today": float(revenue_today),
        "revenue_this_week": float(revenue_this_week),
        "revenue_this_month": float(revenue_this_month),
    }

    # Sales trend (last 30 days)
    sales_trend_rows = db.query(
        models.Invoice.invoice_date,
        func.sum(models.Invoice.total_amount).label("revenue"),
        func.count(models.Invoice.id).label("count"),
    ).filter(
        sale_filter,
        models.Invoice.invoice_date >= thirty_days_ago
    ).group_by(
        models.Invoice.invoice_date
    ).order_by(
        models.Invoice.invoice_date
    ).all()

    sales_trend = [
        {
            "date": str(row.invoice_date),
            "revenue": float(row.revenue or 0),
            "count": int(row.count),
        }
        for row in sales_trend_rows
    ]

    # Top products (top 10 by revenue)
    top_products_rows = db.query(
        models.InvoiceItem.product_id,
        models.Product.item.label("product_name"),
        func.sum(models.InvoiceItem.total_price).label("revenue"),
        func.sum(models.InvoiceItem.quantity).label("quantity_sold"),
    ).join(
        models.Invoice, models.InvoiceItem.invoice_id == models.Invoice.id
    ).join(
        models.Product, models.InvoiceItem.product_id == models.Product.id
    ).filter(
        models.Invoice.invoice_type == 'sale',
        models.Invoice.status == 'active'
    ).group_by(
        models.InvoiceItem.product_id,
        models.Product.item
    ).order_by(
        func.sum(models.InvoiceItem.total_price).desc()
    ).limit(10).all()

    top_products = [
        {
            "product_id": str(row.product_id),
            "product_name": row.product_name,
            "revenue": float(row.revenue or 0),
            "quantity_sold": int(row.quantity_sold or 0),
        }
        for row in top_products_rows
    ]

    # Top customers (top 10 by total spent)
    top_customers_rows = db.query(
        models.Invoice.customer_id,
        models.Customer.name.label("customer_name"),
        func.sum(models.Invoice.total_amount).label("total_spent"),
        func.count(models.Invoice.id).label("invoice_count"),
    ).join(
        models.Customer, models.Invoice.customer_id == models.Customer.id
    ).filter(
        sale_filter
    ).group_by(
        models.Invoice.customer_id,
        models.Customer.name
    ).order_by(
        func.sum(models.Invoice.total_amount).desc()
    ).limit(10).all()

    top_customers = [
        {
            "customer_id": str(row.customer_id),
            "customer_name": row.customer_name,
            "total_spent": float(row.total_spent or 0),
            "invoice_count": int(row.invoice_count),
        }
        for row in top_customers_rows
    ]

    # Stock health
    total_stock_value = db.query(
        func.coalesce(func.sum(models.ProductBatch.remaining_qty * models.ProductBatch.purchase_price), 0)
    ).filter(
        models.ProductBatch.disabled == False
    ).scalar()

    product_count = db.query(
        func.count(models.Product.id)
    ).filter(
        models.Product.disabled == False
    ).scalar()

    low_stock_rows = db.query(
        models.Product.id,
        models.Product.item.label("product_name"),
        func.coalesce(func.sum(models.ProductBatch.remaining_qty), 0).label("total_remaining"),
    ).outerjoin(
        models.ProductBatch, and_(
            models.Product.id == models.ProductBatch.product_id,
            models.ProductBatch.disabled == False
        )
    ).filter(
        models.Product.disabled == False
    ).group_by(
        models.Product.id,
        models.Product.item
    ).having(
        func.coalesce(func.sum(models.ProductBatch.remaining_qty), 0) <= 5
    ).order_by(
        func.coalesce(func.sum(models.ProductBatch.remaining_qty), 0)
    ).limit(20).all()

    low_stock_items = [
        {
            "product_id": str(row.id),
            "product_name": row.product_name,
            "remaining_qty": int(row.total_remaining),
        }
        for row in low_stock_rows
    ]

    stock_health = {
        "total_value": float(total_stock_value),
        "product_count": int(product_count),
        "low_stock_items": low_stock_items,
    }

    # Purchase vs Sales
    total_purchased = db.query(
        func.coalesce(func.sum(models.ProductBatch.quantity * models.ProductBatch.purchase_price), 0)
    ).filter(
        models.ProductBatch.disabled == False
    ).scalar()

    total_sold = db.query(
        func.coalesce(func.sum(models.Invoice.total_amount), 0)
    ).filter(sale_filter).scalar()

    purchase_vs_sales = {
        "total_purchased": float(total_purchased),
        "total_sold": float(total_sold),
    }

    return {
        "sales_metrics": sales_metrics,
        "sales_trend": sales_trend,
        "top_products": top_products,
        "top_customers": top_customers,
        "stock_health": stock_health,
        "purchase_vs_sales": purchase_vs_sales,
    }
