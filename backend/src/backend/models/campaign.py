import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.session import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Details ───────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    setting: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # active | hiatus | completed
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    sessions: Mapped[list["Session"]] = relationship(  # type: ignore[name-defined]
        back_populates="campaign", cascade="all, delete-orphan"
    )
    characters: Mapped[list["Character"]] = relationship(  # type: ignore[name-defined]
        back_populates="campaign", cascade="all, delete-orphan"
    )
    campaign_members: Mapped[list["CampaignMember"]] = relationship(  # type: ignore[name-defined]
        back_populates="campaign", cascade="all, delete-orphan"
    )
    quests: Mapped[list["Quest"]] = relationship(  # type: ignore[name-defined]
        back_populates="campaign", cascade="all, delete-orphan"
    )
    notes: Mapped[list["Note"]] = relationship(  # type: ignore[name-defined]
        back_populates="campaign", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Campaign id={self.id} name={self.name}>"