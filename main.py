from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os

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
    purchase_bills,
    gst_returns,
    auth as auth_router,
    price_levels,
    product_price_overrides,
    products_csv,
)
from app.database import (
    engine,
    Base,
    SessionLocal,
    set_active_company_schema,
    reset_active_company_schema,
    DEFAULT_COMPANY_SCHEMA,
)
from app import control_models
from app.auth import decode_access_token
from app import audit  # noqa: F401  registers AuditLog on the business Base
from app.db.migrations import run_migrations
from app.accounting import seed_chart_of_accounts

# Tables are managed by Alembic migrations (run on startup)
# Base.metadata.create_all(bind=engine)

app = FastAPI()

# Set up CORS middleware. Tightened from "*" to explicit dev origins so the
# Next.js frontend (port 3000) works while we stop reflecting arbitrary
# origins. Add production origins here before deploying.
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

_allow_origin_regex = os.getenv(
    "FASTAPI_ALLOW_ORIGIN_REGEX", r"^https?://.*\.vercel\.app$"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def company_context_middleware(request: Request, call_next):
    """Resolve the active company for the request and apply it to the DB
    session context.

    - Reads ``Authorization: Bearer <jwt>``; if present and valid, identifies
      the user. Invalid/missing auth is NOT rejected here (routers enforce
      auth via dependencies) so existing unauthenticated endpoints keep
      working during the transition.
    - Reads ``X-Company-Id``; if provided AND the authenticated user has
      access (or is a superuser), the active company schema is set for the
      duration of the request. Otherwise it falls back to the legacy
      DEFAULT_COMPANY_SCHEMA ("sskedata").
    """
    schema_name = DEFAULT_COMPANY_SCHEMA
    company_id = request.headers.get("X-Company-Id")
    auth_header = request.headers.get("Authorization", "")

    user = None
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
        except Exception:
            user_id = None
        if user_id:
            db = SessionLocal()
            try:
                db.connection(execution_options={"schema_translate_map": {}})
                user = (
                    db.query(control_models.User)
                    .filter(control_models.User.id == user_id)
                    .first()
                )
                if company_id and user is not None:
                    company = (
                        db.query(control_models.Company)
                        .filter(control_models.Company.id == company_id)
                        .first()
                    )
                    if company is not None and company.is_active:
                        has_access = user.is_superuser or any(
                            str(a.company_id) == str(company.id) for a in user.accesses
                        )
                        if has_access:
                            schema_name = company.schema_name
            finally:
                db.close()

    token_ctx = set_active_company_schema(schema_name)
    try:
        response = await call_next(request)
    finally:
        reset_active_company_schema(token_ctx)
    return response


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


app.include_router(auth_router.router)
app.include_router(customers.router)
app.include_router(product_categories.router)
app.include_router(products_csv.router)  # must be before products.router (static paths win over /{id})
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
app.include_router(purchase_bills.router)
app.include_router(gst_returns.router)
app.include_router(price_levels.router)
app.include_router(product_price_overrides.router)


# This is important for Vercel
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
