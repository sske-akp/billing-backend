"""Seed an auth user + company into the control schema (sske_control).

Run AFTER `alembic upgrade head` (which creates the sske_control tables).

Usage:
    python seed_auth.py <email> <password> <company_name> <company_schema>

Example:
    python seed_auth.py admin@sske.com "s3cret" "SSKE Electricals" sskedata

The user is created as a superuser, so GET /auth/companies returns every
active company (no per-role access rows needed). The script is idempotent:
- a company is matched by its schema_name (created if absent, name refreshed);
- a user is matched by email (created if absent, password reset if present).
Run it again with a different company name/schema to register more companies
for the same login (e.g. to test switching between sskedata and company2).
"""
import argparse
import sys

from sqlalchemy.exc import ProgrammingError, OperationalError

from app.database import SessionLocal
from app import control_models
from app.auth import hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed an auth user + company.")
    parser.add_argument("email")
    parser.add_argument("password")
    parser.add_argument("company_name")
    parser.add_argument("company_schema")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # --- Company (match by schema_name) --------------------------------
        company = (
            db.query(control_models.Company)
            .filter(control_models.Company.schema_name == args.company_schema)
            .first()
        )
        if company is None:
            company = control_models.Company(
                name=args.company_name,
                schema_name=args.company_schema,
                is_active=True,
            )
            db.add(company)
            company_action = "created"
        else:
            company.name = args.company_name
            company.is_active = True
            company_action = "updated"

        # --- User (match by email) -----------------------------------------
        user = (
            db.query(control_models.User)
            .filter(control_models.User.email == args.email)
            .first()
        )
        if user is None:
            user = control_models.User(
                email=args.email,
                hashed_password=hash_password(args.password),
                is_active=True,
                is_superuser=True,
            )
            db.add(user)
            user_action = "created"
        else:
            user.hashed_password = hash_password(args.password)
            user.is_active = True
            user.is_superuser = True
            user_action = "updated (password reset)"

        db.commit()
    except (ProgrammingError, OperationalError) as exc:
        db.rollback()
        print(
            "ERROR: could not read/write the control schema. Did you run "
            "`alembic upgrade head` first?\n"
            f"  underlying error: {exc.orig if hasattr(exc, 'orig') else exc}",
            file=sys.stderr,
        )
        return 1
    finally:
        db.close()

    print(
        f"OK: company '{args.company_name}' ({args.company_schema}) {company_action}; "
        f"superuser '{args.email}' {user_action}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
