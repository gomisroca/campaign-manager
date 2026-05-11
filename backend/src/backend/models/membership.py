import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.session import Base


class Membership(Base):
    __tablename__ = "memberships"

    # A user can only have one membership per org
    __table_args__ = (
        UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Role ──────────────────────────────────────────────────────────────────
    # owner   — full control, cannot be removed, can delete the org
    # admin   — can manage members and settings, cannot delete the org
    # member  — read/write access to org content, no admin actions
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="member",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    org: Mapped["Org"] = relationship(back_populates="memberships")  # type: ignore[name-defined]
    user: Mapped["User"] = relationship(back_populates="memberships")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Membership user={self.user_id} org={self.org_id} role={self.role}>"