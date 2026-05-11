import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


# ── Request schemas ───────────────────────────────────────────────────────────
class InviteCreate(BaseModel):
    """Body for POST /orgs/{org_id}/invites"""
    email: EmailStr
    role: str = "member"

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ("admin", "member"):
            raise ValueError("Role must be 'admin' or 'member'")
        return v


class InviteAccept(BaseModel):
    """Body for POST /invites/accept"""
    token: str


# ── Response schemas ──────────────────────────────────────────────────────────
class InviteResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    email: str
    role: str
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime
    # Flattened for convenience
    org_name: str
    invited_by_email: str

    model_config = {"from_attributes": True}


class InvitePublicResponse(BaseModel):
    """Returned when looking up an invite by token (before accepting).
    Deliberately minimal — don't leak org internals to unauthenticated users.
    """
    org_name: str
    email: str
    role: str
    is_valid: bool