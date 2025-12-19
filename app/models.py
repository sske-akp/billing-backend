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

    invoice = relationship("Invoice")
    product = relationship("Product")
    batch = relationship("ProductBatch")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number = Column(String, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"))
    invoice_date = Column(Date)
    invoice_type = Column(String)
    total_amount = Column(Numeric)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer")
    items = relationship("InvoiceItem")

class ProductBatch(Base):
    __tablename__ = "product_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    batch_code = Column(String)
    purchase_price = Column(Numeric)
    quantity = Column(Integer)
    remaining_qty = Column(Integer)
    purchase_date = Column(DateTime)
    source_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    disabled = Column(Boolean, default=False)
    discount_value = Column(Numeric)

    product = relationship("Product")

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
