from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import customers, product_categories, products, invoice_items, invoices, product_batches, product_brands, discounts, invoice_reports
from .database import engine, Base
from .db.migrations import run_migrations

# Create database tables
Base.metadata.create_all(bind=engine)

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
    allow_origins=["*"], # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.on_event("startup")
def startup():
    run_migrations()

app.include_router(customers.router)
app.include_router(product_categories.router)
app.include_router(products.router)
app.include_router(invoice_items.router)
app.include_router(invoices.router)
app.include_router(product_batches.router)
app.include_router(product_brands.router)
app.include_router(discounts.router)
app.include_router(invoice_reports.router)
