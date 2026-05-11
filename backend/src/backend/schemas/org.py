import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


# ── Helpers ───────────────────────────────────────────────────────────────────
def slugify(value: str) -> str:
    """Convert a name to a URL-friendly slug. e.g. 'Acme Corp' -> 'acme-corp'"""
    import re
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)   # remove non-word chars
    value = re.sub(r"[\s_]+", "-", value)     # spaces/underscores to hyphens
    value = re.sub(r"-+", "-", value)         # collapse multiple hyphens
    return value.strip("-")


# ── Request schemas ───────────────────────────────────────────────────────────
class OrgCreate(BaseModel):
    """Body for POST /orgs"""
    name: str
    slug: str | None = None  # auto-generated from name if not provided

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Organisation name cannot be empty")
        if len(v) > 255:
            raise ValueError("Organisation name must be 255 characters or fewer")
        return v

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        import re
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError(
                "Slug may only contain lowercase letters, numbers, and hyphens, "
                "and cannot start or end with a hyphen"
            )
        if len(v) > 255:
            raise ValueError("Slug must be 255 characters or fewer")
        return v


class OrgUpdate(BaseModel):
    """Body for PATCH /orgs/{org_id}"""
    name: str | None = None
    logo_url: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Organisation name cannot be empty")
        return v


# ── Response schemas ──────────────────────────────────────────────────────────
class OrgResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None
    plan: str
    subscription_status: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberResponse(BaseModel):
    """A user within an org, with their role."""
    user_id: uuid.UUID
    org_id: uuid.UUID
    role: str
    joined_at: datetime
    # Flattened user fields for convenience — avoids a nested object in the UI
    email: str
    full_name: str | None
    avatar_url: str | None

    model_config = {"from_attributes": True}


class OrgWithRoleResponse(BaseModel):
    """Returned in list endpoints — includes the current user's role in the org."""
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None
    plan: str
    role: str  # current user's role in this org

    model_config = {"from_attributes": True}