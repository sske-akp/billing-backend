"""Accounting utility functions for automatic journal entry creation."""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models

# Payment method to account code mapping
PAYMENT_METHOD_ACCOUNT_MAP = {
    "cash": "1000",
    "upi": "1020",
    "card": "1010",
    "bank_transfer": "1010",
    "cheque": "1010",
}


def _get_account_by_code(db: Session, code: str) -> models.Account:
    """Fetch an account by its code. Raises ValueError if not found."""
    account = db.query(models.Account).filter(models.Account.code == code).first()
    if not account:
        raise ValueError(f"Account with code {code} not found. Run chart of accounts seed first.")
    return account


def _generate_entry_number(db: Session, entry_date: date) -> str:
    """Generate a unique journal entry number in JE-YYYYMMDD-NNN format."""
    date_str = entry_date.strftime("%Y%m%d")
    prefix = f"JE-{date_str}-"

    # Find the highest existing entry number for this date
    last_entry = (
        db.query(models.JournalEntry)
        .filter(models.JournalEntry.entry_number.like(f"{prefix}%"))
        .order_by(models.JournalEntry.entry_number.desc())
        .first()
    )

    if last_entry:
        last_seq = int(last_entry.entry_number.split("-")[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1

    return f"{prefix}{next_seq:03d}"


def _create_journal_entry(
    db: Session,
    entry_date: date,
    description: str,
    reference_type: str,
    reference_id,
    lines: list[dict],
) -> models.JournalEntry:
    """Create a journal entry with lines. All lines must balance (sum debit = sum credit)."""
    total_debit = sum(Decimal(str(l.get("debit", 0))) for l in lines)
    total_credit = sum(Decimal(str(l.get("credit", 0))) for l in lines)

    if total_debit != total_credit:
        raise ValueError(
            f"Journal entry does not balance: debit={total_debit}, credit={total_credit}"
        )

    entry_number = _generate_entry_number(db, entry_date)

    journal_entry = models.JournalEntry(
        entry_number=entry_number,
        entry_date=entry_date,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        is_auto=True,
    )
    db.add(journal_entry)
    db.flush()

    for line_data in lines:
        line = models.JournalLine(
            journal_entry_id=journal_entry.id,
            account_id=line_data["account_id"],
            debit=Decimal(str(line_data.get("debit", 0))),
            credit=Decimal(str(line_data.get("credit", 0))),
            description=line_data.get("description"),
        )
        db.add(line)

    return journal_entry


def _compute_cogs(db: Session, items) -> Decimal:
    """Compute cost of goods sold for a set of invoice items using batch-level
    (specific-identification) costing. Each item pins a batch_id, so the cost is
    the batch purchase_price * quantity. Items without a batch contribute 0."""
    cogs = Decimal("0")
    for item in items:
        if not item.batch_id:
            continue
        batch = (
            db.query(models.ProductBatch)
            .filter(models.ProductBatch.id == item.batch_id)
            .first()
        )
        if batch and batch.purchase_price is not None:
            cogs += Decimal(str(batch.purchase_price)) * Decimal(str(item.quantity or 0))
    return cogs


def create_sale_journal_entry(db: Session, invoice: models.Invoice) -> models.JournalEntry:
    """Create journal entry for a sale invoice.
    DR Accounts Receivable (total_amount)
    CR Sales Revenue (base amount, pre-GST)
    CR GST Output Tax (gst amount)
    DR Cost of Goods Sold (batch cost)
    CR Inventory (batch cost)
    """
    accounts_receivable = _get_account_by_code(db, "1100")
    sales_revenue = _get_account_by_code(db, "4000")
    gst_output = _get_account_by_code(db, "2100")

    total = Decimal(str(invoice.total_amount or 0))
    # Calculate base and GST from invoice items
    base_amount = Decimal("0")
    gst_amount = Decimal("0")
    for item in invoice.items:
        line_base = Decimal(str(item.selling_price or 0)) * Decimal(str(item.quantity or 0))
        line_tax = line_base * Decimal(str(item.tax_percent or 0)) / Decimal("100")
        base_amount += line_base
        gst_amount += line_tax

    # Use abs(total) to handle any rounding differences
    total = base_amount + gst_amount

    lines = [
        {"account_id": accounts_receivable.id, "debit": total, "credit": Decimal("0"), "description": "Accounts Receivable"},
        {"account_id": sales_revenue.id, "debit": Decimal("0"), "credit": base_amount, "description": "Sales Revenue"},
        {"account_id": gst_output.id, "debit": Decimal("0"), "credit": gst_amount, "description": "GST Output Tax"},
    ]

    # Post cost of goods sold against inventory so gross profit and the
    # inventory asset are both correct.
    cogs = _compute_cogs(db, invoice.items)
    if cogs > 0:
        cogs_account = _get_account_by_code(db, "5000")
        inventory = _get_account_by_code(db, "1200")
        lines.append({"account_id": cogs_account.id, "debit": cogs, "credit": Decimal("0"), "description": "Cost of Goods Sold"})
        lines.append({"account_id": inventory.id, "debit": Decimal("0"), "credit": cogs, "description": "Inventory"})

    return _create_journal_entry(
        db,
        entry_date=invoice.invoice_date or date.today(),
        description=f"Sale invoice {invoice.invoice_number}",
        reference_type="invoice",
        reference_id=invoice.id,
        lines=lines,
    )


def create_payment_journal_entry(db: Session, payment: models.Payment) -> models.JournalEntry:
    """Create journal entry for a payment received.
    DR Payment Method Account (amount)
    CR Accounts Receivable (amount)
    """
    method_code = PAYMENT_METHOD_ACCOUNT_MAP.get(payment.payment_method, "1000")
    payment_account = _get_account_by_code(db, method_code)
    accounts_receivable = _get_account_by_code(db, "1100")

    amount = Decimal(str(payment.amount))

    lines = [
        {"account_id": payment_account.id, "debit": amount, "credit": Decimal("0"), "description": f"Payment via {payment.payment_method}"},
        {"account_id": accounts_receivable.id, "debit": Decimal("0"), "credit": amount, "description": "Accounts Receivable"},
    ]

    return _create_journal_entry(
        db,
        entry_date=payment.payment_date or date.today(),
        description=f"Payment received for invoice",
        reference_type="payment",
        reference_id=payment.id,
        lines=lines,
    )


def create_supplier_payment_journal_entry(db: Session, payment: models.Payment) -> models.JournalEntry:
    """Create journal entry for a payment made to a supplier.
    DR Accounts Payable (amount)
    CR Payment Method Account (amount)
    """
    method_code = PAYMENT_METHOD_ACCOUNT_MAP.get(payment.payment_method, "1000")
    payment_account = _get_account_by_code(db, method_code)
    accounts_payable = _get_account_by_code(db, "2000")

    amount = Decimal(str(payment.amount))

    lines = [
        {"account_id": accounts_payable.id, "debit": amount, "credit": Decimal("0"), "description": "Accounts Payable"},
        {"account_id": payment_account.id, "debit": Decimal("0"), "credit": amount, "description": f"Payment via {payment.payment_method}"},
    ]

    return _create_journal_entry(
        db,
        entry_date=payment.payment_date or date.today(),
        description=f"Payment made to supplier",
        reference_type="payment",
        reference_id=payment.id,
        lines=lines,
    )


def create_credit_note_journal_entry(db: Session, credit_note: models.Invoice) -> models.JournalEntry:
    """Create journal entry for a credit note (sales return).
    DR Sales Returns (base amount)
    DR GST Output Tax (gst amount)
    CR Accounts Receivable (total amount)
    """
    sales_returns = _get_account_by_code(db, "4010")
    gst_output = _get_account_by_code(db, "2100")
    accounts_receivable = _get_account_by_code(db, "1100")

    # Credit note total_amount is negative, so use abs
    base_amount = Decimal("0")
    gst_amount = Decimal("0")
    for item in credit_note.items:
        line_base = Decimal(str(item.selling_price or 0)) * Decimal(str(item.quantity or 0))
        line_tax = line_base * Decimal(str(item.tax_percent or 0)) / Decimal("100")
        base_amount += line_base
        gst_amount += line_tax

    total = base_amount + gst_amount

    lines = [
        {"account_id": sales_returns.id, "debit": base_amount, "credit": Decimal("0"), "description": "Sales Returns"},
        {"account_id": gst_output.id, "debit": gst_amount, "credit": Decimal("0"), "description": "GST Output Tax reversal"},
        {"account_id": accounts_receivable.id, "debit": Decimal("0"), "credit": total, "description": "Accounts Receivable"},
    ]

    # Reverse the cost of goods sold: returned stock goes back into inventory.
    cogs = _compute_cogs(db, credit_note.items)
    if cogs > 0:
        cogs_account = _get_account_by_code(db, "5000")
        inventory = _get_account_by_code(db, "1200")
        lines.append({"account_id": inventory.id, "debit": cogs, "credit": Decimal("0"), "description": "Inventory"})
        lines.append({"account_id": cogs_account.id, "debit": Decimal("0"), "credit": cogs, "description": "Cost of Goods Sold reversal"})

    return _create_journal_entry(
        db,
        entry_date=credit_note.invoice_date or date.today(),
        description=f"Credit note {credit_note.invoice_number}",
        reference_type="credit_note",
        reference_id=credit_note.id,
        lines=lines,
    )


def create_purchase_journal_entry(db: Session, bill: models.PurchaseBill) -> models.JournalEntry:
    """Create journal entry for a purchase bill.
    DR Inventory (goods value, ex-GST)
    DR GST Input Tax (recoverable input GST)
    CR Accounts Payable (bill total, incl. GST)
    """
    inventory = _get_account_by_code(db, "1200")
    gst_input = _get_account_by_code(db, "2110")
    accounts_payable = _get_account_by_code(db, "2000")

    base_amount = Decimal("0")
    gst_amount = Decimal("0")
    for item in bill.items:
        line_base = Decimal(str(item.purchase_price or 0)) * Decimal(str(item.quantity or 0))
        line_tax = line_base * Decimal(str(item.tax_percent or 0)) / Decimal("100")
        base_amount += line_base
        gst_amount += line_tax

    total = base_amount + gst_amount

    lines = [
        {"account_id": inventory.id, "debit": base_amount, "credit": Decimal("0"), "description": "Inventory"},
    ]
    if gst_amount > 0:
        lines.append({"account_id": gst_input.id, "debit": gst_amount, "credit": Decimal("0"), "description": "GST Input Tax"})
    lines.append({"account_id": accounts_payable.id, "debit": Decimal("0"), "credit": total, "description": "Accounts Payable"})

    supplier_name = bill.supplier.name if bill.supplier else "Unknown"

    return _create_journal_entry(
        db,
        entry_date=bill.bill_date or date.today(),
        description=f"Purchase bill {bill.bill_number or ''} from {supplier_name}".strip(),
        reference_type="purchase",
        reference_id=bill.id,
        lines=lines,
    )


# Default chart of accounts seed data
DEFAULT_ACCOUNTS = [
    {"code": "1000", "name": "Cash", "account_type": "asset"},
    {"code": "1010", "name": "Bank Account", "account_type": "asset"},
    {"code": "1020", "name": "UPI Collections", "account_type": "asset"},
    {"code": "1100", "name": "Accounts Receivable", "account_type": "asset"},
    {"code": "1200", "name": "Inventory", "account_type": "asset"},
    {"code": "2000", "name": "Accounts Payable", "account_type": "liability"},
    {"code": "2100", "name": "GST Output Tax", "account_type": "liability"},
    {"code": "2110", "name": "GST Input Tax", "account_type": "liability"},
    {"code": "3000", "name": "Owner's Equity", "account_type": "equity"},
    {"code": "4000", "name": "Sales Revenue", "account_type": "income"},
    {"code": "4010", "name": "Sales Returns", "account_type": "income"},
    {"code": "5000", "name": "Cost of Goods Sold", "account_type": "expense"},
    {"code": "5100", "name": "Purchase Expense", "account_type": "expense"},
]


def seed_chart_of_accounts(db: Session) -> None:
    """Seed the default chart of accounts if they don't exist yet."""
    existing_count = db.query(models.Account).filter(models.Account.is_system == True).count()
    if existing_count > 0:
        return  # Already seeded

    for acct in DEFAULT_ACCOUNTS:
        db_account = models.Account(
            code=acct["code"],
            name=acct["name"],
            account_type=acct["account_type"],
            is_system=True,
            disabled=False,
        )
        db.add(db_account)

    db.commit()
