from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    customers,
    product_categories,
    products,
    invoice_items,
    invoices,
    product_batches,
    product_brands,
    discounts,
    invoice_reports,
    suppliers,
    reports,
    accounts,
    journal_entries,
    payments,
    accounting_reports,
)
from app.database import engine, Base, SessionLocal
from app.db.migrations import run_migrations
from app.accounting import seed_chart_of_accounts

# Tables are managed by Alembic migrations (run on startup)
# Base.metadata.create_all(bind=engine)

app = FastAPI()

# Set up CORS middleware
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    # Add other origins as needed for your frontend application
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/run-migrations")
def run_db_migrations():
    run_migrations()
    return {"status": "migrations complete"}


@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        seed_chart_of_accounts(db)
    finally:
        db.close()


app.include_router(customers.router)
app.include_router(product_categories.router)
app.include_router(products.router)
app.include_router(invoice_items.router)
app.include_router(invoices.router)
app.include_router(product_batches.router)
app.include_router(product_brands.router)
app.include_router(discounts.router)
app.include_router(invoice_reports.router)
app.include_router(suppliers.router)
app.include_router(reports.router)
app.include_router(accounts.router)
app.include_router(journal_entries.router)
app.include_router(payments.router)
app.include_router(accounting_reports.router)


# This is important for Vercel
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
