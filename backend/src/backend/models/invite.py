import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.session import Base


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Invite details ────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")

    # Secure random token included in the invite link.
    # Indexed for fast lookup when the recipient clicks the link.
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    org: Mapped["Org"] = relationship()          # type: ignore[name-defined]
    inviter: Mapped["User"] = relationship()     # type: ignore[name-defined]

    @property
    def is_expired(self) -> bool:
        from datetime import UTC, datetime, timezone
        now = datetime.now(UTC)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now > expires

    @property
    def is_accepted(self) -> bool:
        return self.accepted_at is not None

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.is_accepted

    def __repr__(self) -> str:
        return f"<Invite id={self.id} email={self.email} org={self.org_id}>"