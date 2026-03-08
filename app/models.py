from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base
import uuid
from datetime import datetime

class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    address = Column(String)
    gstin = Column(String)
    phone_number = Column(String)
    email = Column(String)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Discount(Base):
    __tablename__ = "discounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    name = Column(String)
    value = Column(Numeric, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    category_id = Column(UUID(as_uuid=True), ForeignKey("product_categories.id"))

    product = relationship("Product")
    category = relationship("ProductCategory")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    batch_id = Column(UUID(as_uuid=True), ForeignKey("product_batches.id"))
    quantity = Column(Integer)
    selling_price = Column(Numeric)
    tax_percent = Column(Numeric)
    total_price = Column(Numeric)
    is_official = Column(Boolean)
    reference_item_id = Column(UUID(as_uuid=True), ForeignKey("invoice_items.id"), nullable=True)

    invoice = relationship("Invoice")
    product = relationship("Product")
    batch = relationship("ProductBatch")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number = Column(String, nullable=False, unique=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"))
    invoice_date = Column(Date)
    invoice_type = Column(String)
    total_amount = Column(Numeric)
    status = Column(String, default='active')
    reference_invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    payment_status = Column(String, default='unpaid')
    payment_method = Column(String, nullable=True)
    due_date = Column(Date, nullable=True)
    amount_paid = Column(Numeric, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer")
    items = relationship("InvoiceItem", foreign_keys="InvoiceItem.invoice_id")
    payments = relationship("Payment", back_populates="invoice")

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    phone_number = Column(String)
    email = Column(String)
    address = Column(String)
    gstin = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProductBatch(Base):
    __tablename__ = "product_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)
    batch_code = Column(String)
    purchase_price = Column(Numeric)
    quantity = Column(Integer)
    remaining_qty = Column(Integer)
    purchase_date = Column(DateTime)
    source_type = Column(String)
    status = Column(String, default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)
    disabled = Column(Boolean, default=False)
    discount_value = Column(Numeric)

    product = relationship("Product")
    supplier = relationship("Supplier")

class ProductBrand(Base):
    __tablename__ = "product_brands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand = Column(String)
    company = Column(String)
    disabled = Column(Boolean, default=False)

    products = relationship("Product")

class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    disabled = Column(Boolean, default=False)

    products = relationship("Product")
    discounts = relationship("Discount")

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item = Column(String, nullable=False)
    hsncode = Column(String)
    unit = Column(String)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("product_brands.id"))
    category_id = Column(UUID(as_uuid=True), ForeignKey("product_categories.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    disabled = Column(Boolean, default=False)
    gst_rate = Column(Numeric, default=18)

    brand = relationship("ProductBrand")
    category = relationship("ProductCategory")
    batches = relationship("ProductBatch")
    invoice_items = relationship("InvoiceItem")

# Note: The 'stock' and 'stock_summary' tables seem to have integer primary keys
# and might not fit the UUID pattern used in other tables.
# I will define them based on the schema provided, assuming integer primary keys.

class Stock(Base):
    __tablename__ = "stock"

    id = Column(Integer, primary_key=True) # Assuming this is an integer primary key based on schema
    company = Column(String)
    item = Column(String)
    quantity = Column(Numeric) # Using Numeric for real type
    priceperunit = Column(Numeric) # Using Numeric for real type
    totalprice = Column(Numeric) # Using Numeric for real type
    lastupdatetimestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

class StockSummary(Base):
    __tablename__ = "stock_summary"

    id = Column(Integer, primary_key=True) # Assuming this is an integer primary key based on schema
    item = Column(String) # Using String for text type
    location = Column(String) # Using String for text type
    quantity = Column(Numeric) # Using Numeric for double precision type
    rate = Column(Numeric) # Using Numeric for double precision type
    value = Column(Numeric) # Using Numeric for double precision type


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    account_type = Column(String, nullable=False)  # asset, liability, income, expense, equity
    parent_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    is_system = Column(Boolean, default=True)
    disabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    parent = relationship("Account", remote_side="Account.id")
    journal_lines = relationship("JournalLine", back_populates="account")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_number = Column(String, unique=True, nullable=False)
    entry_date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    reference_type = Column(String, nullable=True)  # invoice, credit_note, payment, purchase, adjustment
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    is_auto = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    lines = relationship("JournalLine", back_populates="journal_entry", cascade="all, delete-orphan")


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    debit = Column(Numeric, default=0)
    credit = Column(Numeric, default=0)
    description = Column(String, nullable=True)

    journal_entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account", back_populates="journal_lines")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    amount = Column(Numeric, nullable=False)
    payment_method = Column(String, nullable=False)  # cash, upi, card, bank_transfer, cheque
    payment_date = Column(Date, nullable=False)
    reference_number = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="payments")
    customer = relationship("Customer")
    journal_entry = relationship("JournalEntry")
