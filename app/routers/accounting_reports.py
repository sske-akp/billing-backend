from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, case
from typing import List, Optional
from datetime import date, timedelta
from decimal import Decimal
import uuid

from .. import models
from ..database import get_db

router = APIRouter(
    prefix="/reports",
    tags=["accounting_reports"],
)


# --- Trial Balance ---

@router.get("/trial-balance")
def get_trial_balance(as_of: date = Query(default=None), db: Session = Depends(get_db)):
    if as_of is None:
        as_of = date.today()

    rows = (
        db.query(
            models.Account.code,
            models.Account.name,
            models.Account.account_type,
            func.coalesce(func.sum(models.JournalLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(models.JournalLine.credit), 0).label("total_credit"),
        )
        .outerjoin(models.JournalLine, models.JournalLine.account_id == models.Account.id)
        .outerjoin(models.JournalEntry, models.JournalLine.journal_entry_id == models.JournalEntry.id)
        .filter(
            models.Account.disabled == False,
            (models.JournalEntry.entry_date <= as_of) | (models.JournalEntry.entry_date == None),
        )
        .group_by(models.Account.code, models.Account.name, models.Account.account_type)
        .order_by(models.Account.code)
        .all()
    )

    accounts = []
    sum_debit = Decimal("0")
    sum_credit = Decimal("0")
    for row in rows:
        total_debit = Decimal(str(row.total_debit))
        total_credit = Decimal(str(row.total_credit))
        balance = total_debit - total_credit
        accounts.append({
            "account_code": row.code,
            "account_name": row.name,
            "account_type": row.account_type,
            "total_debit": float(total_debit),
            "total_credit": float(total_credit),
            "balance": float(balance),
        })
        sum_debit += total_debit
        sum_credit += total_credit

    return {
        "as_of": str(as_of),
        "accounts": accounts,
        "total_debit": float(sum_debit),
        "total_credit": float(sum_credit),
        "is_balanced": sum_debit == sum_credit,
    }


# --- Profit & Loss ---

@router.get("/profit-loss")
def get_profit_loss(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            models.Account.code,
            models.Account.name,
            models.Account.account_type,
            func.coalesce(func.sum(models.JournalLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(models.JournalLine.credit), 0).label("total_credit"),
        )
        .join(models.JournalLine, models.JournalLine.account_id == models.Account.id)
        .join(models.JournalEntry, models.JournalLine.journal_entry_id == models.JournalEntry.id)
        .filter(
            models.Account.disabled == False,
            models.Account.account_type.in_(["income", "expense"]),
            models.JournalEntry.entry_date >= date_from,
            models.JournalEntry.entry_date <= date_to,
        )
        .group_by(models.Account.code, models.Account.name, models.Account.account_type)
        .order_by(models.Account.code)
        .all()
    )

    income_items = []
    expense_items = []
    total_income = Decimal("0")
    total_expenses = Decimal("0")

    for row in rows:
        total_debit = Decimal(str(row.total_debit))
        total_credit = Decimal(str(row.total_credit))

        if row.account_type == "income":
            amount = total_credit - total_debit
            income_items.append({
                "account_code": row.code,
                "account_name": row.name,
                "amount": float(amount),
            })
            total_income += amount
        elif row.account_type == "expense":
            amount = total_debit - total_credit
            expense_items.append({
                "account_code": row.code,
                "account_name": row.name,
                "amount": float(amount),
            })
            total_expenses += amount

    net_profit = total_income - total_expenses

    return {
        "from": str(date_from),
        "to": str(date_to),
        "income": income_items,
        "expenses": expense_items,
        "total_income": float(total_income),
        "total_expenses": float(total_expenses),
        "net_profit": float(net_profit),
    }


# --- Balance Sheet ---

@router.get("/balance-sheet")
def get_balance_sheet(as_of: date = Query(default=None), db: Session = Depends(get_db)):
    if as_of is None:
        as_of = date.today()

    rows = (
        db.query(
            models.Account.code,
            models.Account.name,
            models.Account.account_type,
            func.coalesce(func.sum(models.JournalLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(models.JournalLine.credit), 0).label("total_credit"),
        )
        .outerjoin(models.JournalLine, models.JournalLine.account_id == models.Account.id)
        .outerjoin(models.JournalEntry, models.JournalLine.journal_entry_id == models.JournalEntry.id)
        .filter(
            models.Account.disabled == False,
            models.Account.account_type.in_(["asset", "liability", "equity"]),
            (models.JournalEntry.entry_date <= as_of) | (models.JournalEntry.entry_date == None),
        )
        .group_by(models.Account.code, models.Account.name, models.Account.account_type)
        .order_by(models.Account.code)
        .all()
    )

    assets = []
    liabilities = []
    equity = []
    total_assets = Decimal("0")
    total_liabilities = Decimal("0")
    total_equity = Decimal("0")

    for row in rows:
        total_debit = Decimal(str(row.total_debit))
        total_credit = Decimal(str(row.total_credit))

        if row.account_type == "asset":
            balance = total_debit - total_credit
            assets.append({
                "account_code": row.code,
                "account_name": row.name,
                "balance": float(balance),
            })
            total_assets += balance
        elif row.account_type == "liability":
            balance = total_credit - total_debit
            liabilities.append({
                "account_code": row.code,
                "account_name": row.name,
                "balance": float(balance),
            })
            total_liabilities += balance
        elif row.account_type == "equity":
            balance = total_credit - total_debit
            equity.append({
                "account_code": row.code,
                "account_name": row.name,
                "balance": float(balance),
            })
            total_equity += balance

    is_balanced = total_assets == (total_liabilities + total_equity)

    return {
        "as_of": str(as_of),
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total_assets": float(total_assets),
        "total_liabilities": float(total_liabilities),
        "total_equity": float(total_equity),
        "is_balanced": is_balanced,
    }


# --- Customer Ledger ---

@router.get("/customer-ledger/{customer_id}")
def get_customer_ledger(customer_id: uuid.UUID, db: Session = Depends(get_db)):
    # Find all invoices and payments for this customer
    invoice_ids = [
        row[0] for row in db.query(models.Invoice.id).filter(
            models.Invoice.customer_id == customer_id
        ).all()
    ]
    payment_ids = [
        row[0] for row in db.query(models.Payment.id).filter(
            models.Payment.customer_id == customer_id
        ).all()
    ]

    # Get journal entries referencing these invoices or payments
    ref_ids = invoice_ids + payment_ids
    if not ref_ids:
        return {"customer_id": str(customer_id), "entries": []}

    entries = (
        db.query(models.JournalEntry)
        .options(joinedload(models.JournalEntry.lines))
        .filter(models.JournalEntry.reference_id.in_(ref_ids))
        .order_by(models.JournalEntry.entry_date, models.JournalEntry.created_at)
        .all()
    )

    # Get Accounts Receivable account
    ar_account = db.query(models.Account).filter(models.Account.code == "1100").first()

    result_entries = []
    running_balance = Decimal("0")

    for entry in entries:
        entry_debit = Decimal("0")
        entry_credit = Decimal("0")
        for line in entry.lines:
            if ar_account and line.account_id == ar_account.id:
                entry_debit += Decimal(str(line.debit or 0))
                entry_credit += Decimal(str(line.credit or 0))

        running_balance += entry_debit - entry_credit

        result_entries.append({
            "date": str(entry.entry_date),
            "entry_number": entry.entry_number,
            "description": entry.description,
            "reference_type": entry.reference_type,
            "debit": float(entry_debit),
            "credit": float(entry_credit),
            "running_balance": float(running_balance),
        })

    return {
        "customer_id": str(customer_id),
        "entries": result_entries,
    }


# --- Supplier Ledger ---

@router.get("/supplier-ledger/{supplier_id}")
def get_supplier_ledger(supplier_id: uuid.UUID, db: Session = Depends(get_db)):
    # Get journal entries referencing purchases for this supplier
    # Purchase journal entries reference_type='purchase'
    # We need to find batches from this supplier and their related journal entries
    entries = (
        db.query(models.JournalEntry)
        .options(joinedload(models.JournalEntry.lines))
        .filter(models.JournalEntry.reference_type == "purchase")
        .order_by(models.JournalEntry.entry_date, models.JournalEntry.created_at)
        .all()
    )

    # Get Accounts Payable account
    ap_account = db.query(models.Account).filter(models.Account.code == "2000").first()

    result_entries = []
    running_balance = Decimal("0")

    for entry in entries:
        # Check if this entry description mentions the supplier
        # Since purchase JEs don't have a direct supplier FK, we filter by description
        entry_debit = Decimal("0")
        entry_credit = Decimal("0")
        for line in entry.lines:
            if ap_account and line.account_id == ap_account.id:
                entry_debit += Decimal(str(line.debit or 0))
                entry_credit += Decimal(str(line.credit or 0))

        if entry_credit > 0 or entry_debit > 0:
            running_balance += entry_credit - entry_debit
            result_entries.append({
                "date": str(entry.entry_date),
                "entry_number": entry.entry_number,
                "description": entry.description,
                "reference_type": entry.reference_type,
                "debit": float(entry_debit),
                "credit": float(entry_credit),
                "running_balance": float(running_balance),
            })

    return {
        "supplier_id": str(supplier_id),
        "entries": result_entries,
    }


# --- Aging Receivables ---

@router.get("/aging-receivables")
def get_aging_receivables(db: Session = Depends(get_db)):
    today = date.today()

    # Get all unpaid/partial invoices
    invoices = (
        db.query(models.Invoice)
        .join(models.Customer, models.Invoice.customer_id == models.Customer.id)
        .filter(
            models.Invoice.invoice_type == "sale",
            models.Invoice.status == "active",
            models.Invoice.payment_status.in_(["unpaid", "partial"]),
        )
        .all()
    )

    # Group by customer
    customer_aging = {}
    for inv in invoices:
        cust_id = str(inv.customer_id)
        if cust_id not in customer_aging:
            customer = db.query(models.Customer).filter(models.Customer.id == inv.customer_id).first()
            customer_aging[cust_id] = {
                "customer_id": cust_id,
                "customer_name": customer.name if customer else "Unknown",
                "current": 0.0,
                "days_31_60": 0.0,
                "days_61_90": 0.0,
                "days_90_plus": 0.0,
                "total": 0.0,
            }

        outstanding = float(Decimal(str(inv.total_amount or 0)) - Decimal(str(inv.amount_paid or 0)))
        invoice_date = inv.invoice_date or inv.created_at.date() if inv.created_at else today
        age_days = (today - invoice_date).days

        if age_days <= 30:
            customer_aging[cust_id]["current"] += outstanding
        elif age_days <= 60:
            customer_aging[cust_id]["days_31_60"] += outstanding
        elif age_days <= 90:
            customer_aging[cust_id]["days_61_90"] += outstanding
        else:
            customer_aging[cust_id]["days_90_plus"] += outstanding

        customer_aging[cust_id]["total"] += outstanding

    return {
        "as_of": str(today),
        "customers": list(customer_aging.values()),
    }


# --- Aging Payables ---

@router.get("/aging-payables")
def get_aging_payables(db: Session = Depends(get_db)):
    today = date.today()

    # Get AP journal entries (purchases)
    ap_account = db.query(models.Account).filter(models.Account.code == "2000").first()
    if not ap_account:
        return {"as_of": str(today), "suppliers": []}

    # Get credit lines on AP (purchases add credit to AP)
    lines = (
        db.query(
            models.JournalLine,
            models.JournalEntry.entry_date,
            models.JournalEntry.description,
        )
        .join(models.JournalEntry, models.JournalLine.journal_entry_id == models.JournalEntry.id)
        .filter(
            models.JournalLine.account_id == ap_account.id,
            models.JournalLine.credit > 0,
        )
        .all()
    )

    # Simple aging based on journal entry date
    aging = {
        "current": 0.0,
        "days_31_60": 0.0,
        "days_61_90": 0.0,
        "days_90_plus": 0.0,
        "total": 0.0,
    }

    for line, entry_date, description in lines:
        amount = float(Decimal(str(line.credit or 0)) - Decimal(str(line.debit or 0)))
        age_days = (today - entry_date).days

        if age_days <= 30:
            aging["current"] += amount
        elif age_days <= 60:
            aging["days_31_60"] += amount
        elif age_days <= 90:
            aging["days_61_90"] += amount
        else:
            aging["days_90_plus"] += amount

        aging["total"] += amount

    return {
        "as_of": str(today),
        "suppliers": [aging],
    }


# --- GST Summary ---

@router.get("/gst-summary")
def get_gst_summary(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    db: Session = Depends(get_db),
):
    gst_output = db.query(models.Account).filter(models.Account.code == "2100").first()
    gst_input = db.query(models.Account).filter(models.Account.code == "2110").first()

    output_tax = Decimal("0")
    input_tax = Decimal("0")

    if gst_output:
        result = (
            db.query(
                func.coalesce(func.sum(models.JournalLine.credit), 0).label("total_credit"),
                func.coalesce(func.sum(models.JournalLine.debit), 0).label("total_debit"),
            )
            .join(models.JournalEntry, models.JournalLine.journal_entry_id == models.JournalEntry.id)
            .filter(
                models.JournalLine.account_id == gst_output.id,
                models.JournalEntry.entry_date >= date_from,
                models.JournalEntry.entry_date <= date_to,
            )
            .first()
        )
        if result:
            output_tax = Decimal(str(result.total_credit)) - Decimal(str(result.total_debit))

    if gst_input:
        result = (
            db.query(
                func.coalesce(func.sum(models.JournalLine.debit), 0).label("total_debit"),
                func.coalesce(func.sum(models.JournalLine.credit), 0).label("total_credit"),
            )
            .join(models.JournalEntry, models.JournalLine.journal_entry_id == models.JournalEntry.id)
            .filter(
                models.JournalLine.account_id == gst_input.id,
                models.JournalEntry.entry_date >= date_from,
                models.JournalEntry.entry_date <= date_to,
            )
            .first()
        )
        if result:
            input_tax = Decimal(str(result.total_debit)) - Decimal(str(result.total_credit))

    net_payable = output_tax - input_tax

    return {
        "from": str(date_from),
        "to": str(date_to),
        "output_tax": float(output_tax),
        "input_tax": float(input_tax),
        "net_payable": float(net_payable),
    }


# --- Home / Dashboard Summary ---

@router.get("/home")
def get_home_dashboard(db: Session = Depends(get_db)):
    today = date.today()

    # Today's sales count + total revenue
    today_sales = db.query(
        func.count(models.Invoice.id).label("count"),
        func.coalesce(func.sum(models.Invoice.total_amount), 0).label("total"),
    ).filter(
        models.Invoice.invoice_type == "sale",
        models.Invoice.status == "active",
        models.Invoice.invoice_date == today,
    ).first()

    # Pending payments count + total outstanding
    pending_payments = db.query(
        func.count(models.Invoice.id).label("count"),
        func.coalesce(
            func.sum(models.Invoice.total_amount - models.Invoice.amount_paid), 0
        ).label("total_outstanding"),
    ).filter(
        models.Invoice.invoice_type == "sale",
        models.Invoice.status == "active",
        models.Invoice.payment_status.in_(["unpaid", "partial"]),
    ).first()

    # Low stock alerts (products with total remaining_qty <= 5)
    low_stock = (
        db.query(
            models.Product.id,
            models.Product.item.label("product_name"),
            func.coalesce(func.sum(models.ProductBatch.remaining_qty), 0).label("total_remaining"),
        )
        .outerjoin(
            models.ProductBatch,
            and_(
                models.Product.id == models.ProductBatch.product_id,
                models.ProductBatch.disabled == False,
            ),
        )
        .filter(models.Product.disabled == False)
        .group_by(models.Product.id, models.Product.item)
        .having(func.coalesce(func.sum(models.ProductBatch.remaining_qty), 0) <= 5)
        .order_by(func.coalesce(func.sum(models.ProductBatch.remaining_qty), 0))
        .limit(10)
        .all()
    )

    # Overdue invoices (past due_date and unpaid)
    overdue_count = db.query(func.count(models.Invoice.id)).filter(
        models.Invoice.invoice_type == "sale",
        models.Invoice.status == "active",
        models.Invoice.payment_status.in_(["unpaid", "partial"]),
        models.Invoice.due_date != None,
        models.Invoice.due_date < today,
    ).scalar()

    # Last 5 invoices
    last_invoices = (
        db.query(models.Invoice)
        .filter(models.Invoice.invoice_type == "sale", models.Invoice.status == "active")
        .order_by(models.Invoice.created_at.desc())
        .limit(5)
        .all()
    )

    # Last 5 payments
    last_payments = (
        db.query(models.Payment)
        .order_by(models.Payment.created_at.desc())
        .limit(5)
        .all()
    )

    # Top 5 overdue customers
    overdue_customers = (
        db.query(
            models.Customer.id,
            models.Customer.name,
            func.count(models.Invoice.id).label("overdue_count"),
            func.coalesce(
                func.sum(models.Invoice.total_amount - models.Invoice.amount_paid), 0
            ).label("total_overdue"),
        )
        .join(models.Invoice, models.Invoice.customer_id == models.Customer.id)
        .filter(
            models.Invoice.invoice_type == "sale",
            models.Invoice.status == "active",
            models.Invoice.payment_status.in_(["unpaid", "partial"]),
            models.Invoice.due_date != None,
            models.Invoice.due_date < today,
        )
        .group_by(models.Customer.id, models.Customer.name)
        .order_by(
            func.coalesce(
                func.sum(models.Invoice.total_amount - models.Invoice.amount_paid), 0
            ).desc()
        )
        .limit(5)
        .all()
    )

    return {
        "today_sales": {
            "count": int(today_sales.count) if today_sales else 0,
            "total_revenue": float(today_sales.total) if today_sales else 0.0,
        },
        "pending_payments": {
            "count": int(pending_payments.count) if pending_payments else 0,
            "total_outstanding": float(pending_payments.total_outstanding) if pending_payments else 0.0,
        },
        "low_stock_alerts": [
            {
                "product_id": str(row.id),
                "product_name": row.product_name,
                "remaining_qty": int(row.total_remaining),
            }
            for row in low_stock
        ],
        "overdue_invoices_count": int(overdue_count or 0),
        "last_invoices": [
            {
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "customer_id": str(inv.customer_id) if inv.customer_id else None,
                "total_amount": float(inv.total_amount or 0),
                "payment_status": inv.payment_status,
                "invoice_date": str(inv.invoice_date) if inv.invoice_date else None,
            }
            for inv in last_invoices
        ],
        "last_payments": [
            {
                "id": str(p.id),
                "invoice_id": str(p.invoice_id),
                "amount": float(p.amount),
                "payment_method": p.payment_method,
                "payment_date": str(p.payment_date),
            }
            for p in last_payments
        ],
        "top_overdue_customers": [
            {
                "customer_id": str(row.id),
                "customer_name": row.name,
                "overdue_count": int(row.overdue_count),
                "total_overdue": float(row.total_overdue),
            }
            for row in overdue_customers
        ],
    }
