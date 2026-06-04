import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


# ── Campaign ──────────────────────────────────────────────────────────────────
class CampaignCreate(BaseModel):
    name: str
    setting: str | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Campaign name cannot be empty")
        return v


class CampaignUpdate(BaseModel):
    name: str | None = None
    setting: str | None = None
    description: str | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("active", "hiatus", "completed"):
            raise ValueError("Status must be 'active', 'hiatus', or 'completed'")
        return v


class CampaignResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    setting: str | None
    description: str | None
    status: str
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignWithStatsResponse(CampaignResponse):
    """Extended response with counts — used in list views."""
    session_count: int = 0
    member_count: int = 0
    quest_count: int = 0


# ── Session ───────────────────────────────────────────────────────────────────
class SessionCreate(BaseModel):
    title: str
    date: datetime | None = None
    summary: str | None = None
    session_number: int | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Session title cannot be empty")
        return v


class SessionUpdate(BaseModel):
    title: str | None = None
    date: datetime | None = None
    summary: str | None = None
    session_number: int | None = None


class SessionResponse(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    org_id: uuid.UUID
    title: str
    date: datetime | None
    summary: str | None
    session_number: int | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Character ─────────────────────────────────────────────────────────────────
class CharacterCreate(BaseModel):
    name: str
    character_class: str | None = None
    race: str | None = None
    level: int = 1
    notes: str | None = None
    is_npc: bool = False

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Character name cannot be empty")
        return v

    @field_validator("level")
    @classmethod
    def valid_level(cls, v: int) -> int:
        if not 1 <= v <= 20:
            raise ValueError("Level must be between 1 and 20")
        return v


class CharacterUpdate(BaseModel):
    name: str | None = None
    character_class: str | None = None
    race: str | None = None
    level: int | None = None
    notes: str | None = None
    is_alive: bool | None = None

    @field_validator("level")
    @classmethod
    def valid_level(cls, v: int | None) -> int | None:
        if v is not None and not 1 <= v <= 20:
            raise ValueError("Level must be between 1 and 20")
        return v


class CharacterResponse(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    org_id: uuid.UUID
    user_id: uuid.UUID | None
    name: str
    character_class: str | None
    race: str | None
    level: int
    notes: str | None
    is_npc: bool
    is_alive: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Campaign Member ───────────────────────────────────────────────────────────
class CampaignMemberAdd(BaseModel):
    user_id: uuid.UUID
    role: str = "player"

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ("dm", "player"):
            raise ValueError("Role must be 'dm' or 'player'")
        return v


class CampaignMemberResponse(BaseModel):
    user_id: uuid.UUID
    campaign_id: uuid.UUID
    role: str
    character_id: uuid.UUID | None
    joined_at: datetime
    # Flattened user fields
    email: str
    full_name: str | None
    avatar_url: str | None

    model_config = {"from_attributes": True}


# ── Quest ─────────────────────────────────────────────────────────────────────
class QuestCreate(BaseModel):
    title: str
    description: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Quest title cannot be empty")
        return v


class QuestUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("open", "in_progress", "completed", "abandoned"):
            raise ValueError("Invalid quest status")
        return v


class QuestResponse(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    org_id: uuid.UUID
    title: str
    description: str | None
    status: str
    posted_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Note ──────────────────────────────────────────────────────────────────────
class NoteCreate(BaseModel):
    title: str
    content: str | None = None
    category: str = "other"

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Note title cannot be empty")
        return v

    @field_validator("category")
    @classmethod
    def valid_category(cls, v: str) -> str:
        if v not in ("lore", "location", "npc", "item", "other"):
            raise ValueError("Invalid category")
        return v


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None

    @field_validator("category")
    @classmethod
    def valid_category(cls, v: str | None) -> str | None:
        if v is not None and v not in ("lore", "location", "npc", "item", "other"):
            raise ValueError("Invalid category")
        return v


class NoteResponse(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    org_id: uuid.UUID
    title: str
    content: str | None
    category: str
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}