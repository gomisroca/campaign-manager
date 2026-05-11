import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.session import Base


class Org(Base):
    __tablename__ = "orgs"

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # URL-friendly unique identifier, e.g. "acme-corp"
    # Used for subdomain routing and display in the UI
    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # ── Billing ───────────────────────────────────────────────────────────────
    plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="free",
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    # trialing | active | past_due | canceled | unpaid
    subscription_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="org", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Org id={self.id} slug={self.slug}>"