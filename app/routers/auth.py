"""Auth router: login, current user, accessible companies.

Pydantic request/response schemas are defined inline here (rather than in the
shared app/schemas.py) to avoid colliding with Phase 2's parallel edits to
schemas.py.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from .. import control_models
from ..control_db import get_control_db
from ..auth import (
    create_access_token,
    verify_password,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Schemas ---------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class CompanyResponse(BaseModel):
    id: str
    name: str
    schema_name: str
    gstin: Optional[str] = None
    state_code: Optional[str] = None
    role: Optional[str] = None

    class Config:
        from_attributes = True


# --- Endpoints -------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, control_db: Session = Depends(get_control_db)):
    user = (
        control_db.query(control_models.User)
        .filter(control_models.User.email == payload.email)
        .first()
    )
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email},
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def read_me(current_user: control_models.User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
    )


@router.get("/companies", response_model=List[CompanyResponse])
def list_companies(
    current_user: control_models.User = Depends(get_current_user),
    control_db: Session = Depends(get_control_db),
):
    """List companies the current user can access.

    Superusers see all active companies; regular users see only those granted
    via UserCompanyAccess.
    """
    results: List[CompanyResponse] = []
    if current_user.is_superuser:
        companies = (
            control_db.query(control_models.Company)
            .filter(control_models.Company.is_active == True)  # noqa: E712
            .all()
        )
        for company in companies:
            results.append(
                CompanyResponse(
                    id=str(company.id),
                    name=company.name,
                    schema_name=company.schema_name,
                    gstin=company.gstin,
                    state_code=company.state_code,
                    role="superuser",
                )
            )
        return results

    for access in current_user.accesses:
        company = access.company
        if company is None or not company.is_active:
            continue
        results.append(
            CompanyResponse(
                id=str(company.id),
                name=company.name,
                schema_name=company.schema_name,
                gstin=company.gstin,
                state_code=company.state_code,
                role=access.role.name if access.role else None,
            )
        )
    return results
