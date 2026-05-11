import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


# ── Shared ────────────────────────────────────────────────────────────────────
# Fields common to multiple schemas are defined once here and reused below.


# ── Request schemas (incoming data) ──────────────────────────────────────────
class UserRegister(BaseModel):
    """Body for POST /auth/register"""
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    """Body for POST /auth/login"""
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    """Body for POST /auth/forgot-password"""
    email: EmailStr


class PasswordReset(BaseModel):
    """Body for POST /auth/reset-password"""
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


# ── Response schemas (outgoing data) ─────────────────────────────────────────
class UserResponse(BaseModel):
    """Returned whenever a user object is included in a response."""
    id: uuid.UUID
    email: str
    full_name: str | None
    avatar_url: str | None
    email_verified_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Returned on successful login or register."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Body for POST /auth/refresh"""
    refresh_token: str