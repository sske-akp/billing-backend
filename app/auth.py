"""Authentication & authorization utilities.

Password hashing uses bcrypt directly; JWTs use PyJWT. (We call bcrypt
directly rather than via passlib because passlib 1.7.4 is unmaintained and
its bcrypt backend probe crashes on modern bcrypt >=4.1, which now raises on
the 72-byte limit instead of truncating.) The dependencies resolve the
current user from the ``Authorization: Bearer <token>`` header against the
control schema.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .control_db import get_control_db
from . import control_models

# --- Config (override via env in production) -------------------------------
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-insecure-change-me")
ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# bcrypt only considers the first 72 bytes of a password; truncate explicitly
# so longer inputs hash/verify without raising on bcrypt >=4.1.
_BCRYPT_MAX_BYTES = 72

# tokenUrl is informational (Swagger); login lives at /auth/login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


# --- Password helpers ------------------------------------------------------
def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(pw, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT helpers -----------------------------------------------------------
def create_access_token(
    subject: str,
    extra_claims: Optional[dict] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": subject, "iat": now, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:  # expired, invalid signature, etc.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# --- Dependencies ----------------------------------------------------------
def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    control_db: Session = Depends(get_control_db),
) -> control_models.User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user = (
        control_db.query(control_models.User)
        .filter(control_models.User.id == user_id)
        .first()
    )
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


def get_user_permissions(
    control_db: Session, user: control_models.User, company_id: Optional[str]
) -> set[str]:
    """Resolve the permission set for a user within a given company."""
    if user.is_superuser:
        return {"*"}
    query = control_db.query(control_models.UserCompanyAccess).filter(
        control_models.UserCompanyAccess.user_id == user.id
    )
    if company_id:
        query = query.filter(
            control_models.UserCompanyAccess.company_id == company_id
        )
    perms: set[str] = set()
    for access in query.all():
        if access.role and access.role.permissions:
            try:
                perms.update(json.loads(access.role.permissions))
            except (ValueError, TypeError):
                pass
    return perms


def require_role(*allowed_roles: str):
    """Return a dependency that requires the user to hold one of ``allowed_roles``
    in the active company (via X-Company-Id). Superusers always pass."""

    def _checker(
        user: control_models.User = Depends(get_current_user),
        control_db: Session = Depends(get_control_db),
    ) -> control_models.User:
        if user.is_superuser:
            return user
        role_names = {
            access.role.name
            for access in user.accesses
            if access.role is not None
        }
        if not role_names.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return user

    return _checker
