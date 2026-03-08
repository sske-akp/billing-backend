from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import uuid

class CustomerBase(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    gstin: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class Customer(CustomerBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DiscountBase(BaseModel):
    product_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    value: float
    is_active: Optional[bool] = True
    category_id: Optional[uuid.UUID] = None

class DiscountCreate(DiscountBase):
    pass

class Discount(DiscountBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InvoiceItemBase(BaseModel):
    invoice_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    quantity: Optional[int] = None
    selling_price: Optional[float] = None
    tax_percent: Optional[float] = None
    total_price: Optional[float] = None
    is_official: Optional[bool] = None
    reference_item_id: Optional[uuid.UUID] = None

class InvoiceItemCreate(InvoiceItemBase):
    pass

class InvoiceItem(InvoiceItemBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

class InvoiceBase(BaseModel):
    invoice_number: str
    customer_id: Optional[uuid.UUID] = None
    invoice_date: Optional[date] = None
    invoice_type: Optional[str] = None
    total_amount: Optional[float] = None
    status: Optional[str] = 'active'
    reference_invoice_id: Optional[uuid.UUID] = None
    payment_status: Optional[str] = 'unpaid'
    payment_method: Optional[str] = None
    due_date: Optional[date] = None
    amount_paid: Optional[float] = 0

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceCreateWithItems(InvoiceBase):
    items: List["InvoiceItemCreate"] = []

class Invoice(InvoiceBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[InvoiceItem] = []

    class Config:
        from_attributes = True

class CreditNoteItemCreate(BaseModel):
    reference_item_id: uuid.UUID
    quantity: int

class CreditNoteCreate(BaseModel):
    reference_invoice_id: uuid.UUID
    items: List[CreditNoteItemCreate]

class SupplierBase(BaseModel):
    name: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    gstin: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class Supplier(SupplierBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProductBatchBase(BaseModel):
    product_id: Optional[uuid.UUID] = None
    supplier_id: Optional[uuid.UUID] = None
    batch_code: Optional[str] = None
    purchase_price: Optional[float] = None
    quantity: Optional[int] = None
    remaining_qty: Optional[int] = None
    purchase_date: Optional[datetime] = None
    source_type: Optional[str] = None
    status: Optional[str] = "completed"
    disabled: Optional[bool] = False
    discount_value: Optional[float] = None

class ProductBatchCreate(ProductBatchBase):
    pass

class ProductBatch(ProductBatchBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProductBrandBase(BaseModel):
    brand: Optional[str] = None
    company: Optional[str] = None
    disabled: Optional[bool] = False

class ProductBrandCreate(ProductBrandBase):
    pass

class ProductBrand(ProductBrandBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

class ProductCategoryBase(BaseModel):
    name: Optional[str] = None
    disabled: Optional[bool] = False

class ProductCategoryCreate(ProductCategoryBase):
    pass

class ProductCategory(ProductCategoryBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    item: str
    hsncode: Optional[str] = None
    unit: Optional[str] = None
    brand_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    disabled: Optional[bool] = False
    gst_rate: Optional[float] = 18

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProductWithBatches(Product):
    batches: List[ProductBatch] = []

    class Config:
        from_attributes = True

class StockBase(BaseModel):
    company: Optional[str] = None
    item: Optional[str] = None
    quantity: Optional[float] = None
    priceperunit: Optional[float] = None
    totalprice: Optional[float] = None

class StockCreate(StockBase):
    pass

class Stock(StockBase):
    id: int
    lastupdatetimestamp: Optional[datetime] = None

    class Config:
        from_attributes = True

class StockSummaryBase(BaseModel):
    item: Optional[str] = None
    location: Optional[str] = None
    quantity: Optional[float] = None
    rate: Optional[float] = None
    value: Optional[float] = None

class StockSummaryCreate(StockSummaryBase):
    pass

class StockSummary(StockSummaryBase):
    id: int

    class Config:
        from_attributes = True


# --- Accounting Schemas ---

class AccountBase(BaseModel):
    code: str
    name: str
    account_type: str  # asset, liability, income, expense, equity
    parent_id: Optional[uuid.UUID] = None
    is_system: Optional[bool] = True
    disabled: Optional[bool] = False

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    account_type: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    disabled: Optional[bool] = None

class Account(AccountBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JournalLineBase(BaseModel):
    account_id: uuid.UUID
    debit: Optional[float] = 0
    credit: Optional[float] = 0
    description: Optional[str] = None

class JournalLineCreate(JournalLineBase):
    pass

class JournalLine(JournalLineBase):
    id: uuid.UUID
    journal_entry_id: uuid.UUID

    class Config:
        from_attributes = True


class JournalEntryBase(BaseModel):
    entry_date: date
    description: str
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None

class JournalEntryCreate(JournalEntryBase):
    lines: List[JournalLineCreate]

class JournalEntry(JournalEntryBase):
    id: uuid.UUID
    entry_number: str
    is_auto: Optional[bool] = False
    created_at: Optional[datetime] = None
    lines: List[JournalLine] = []

    class Config:
        from_attributes = True


class PaymentBase(BaseModel):
    invoice_id: uuid.UUID
    customer_id: Optional[uuid.UUID] = None
    amount: float
    payment_method: str  # cash, upi, card, bank_transfer, cheque
    payment_date: date
    reference_number: Optional[str] = None
    notes: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class Payment(PaymentBase):
    id: uuid.UUID
    journal_entry_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
