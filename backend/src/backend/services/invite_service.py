import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.config import get_settings
from backend.models.invite import Invite
from backend.models.membership import Membership
from backend.models.user import User
from backend.schemas.invite import InviteCreate, InvitePublicResponse, InviteResponse

settings = get_settings()

INVITE_EXPIRY_DAYS = 7


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _get_invite_by_token(db: AsyncSession, token: str) -> Invite | None:
    result = await db.execute(
        select(Invite)
        .where(Invite.token == token)
        .options(joinedload(Invite.org), joinedload(Invite.inviter))
    )
    return result.scalar_one_or_none()


async def _already_member(
    db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID
) -> bool:
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.org_id == org_id,
        )
    )
    return result.scalar_one_or_none() is not None


# ── Create invite ─────────────────────────────────────────────────────────────
async def create_invite(
    db: AsyncSession,
    org_id: uuid.UUID,
    inviter_id: uuid.UUID,
    data: InviteCreate,
) -> Invite:
    """
    Create a new invite. Raises ValueError if:
    - the email already has a pending (valid) invite for this org
    - the email belongs to an existing member
    """
    # Check for an existing pending invite for this email + org
    existing = await db.execute(
        select(Invite).where(
            Invite.org_id == org_id,
            Invite.email == data.email.lower().strip(),
            Invite.accepted_at.is_(None),
        )
    )
    pending = existing.scalar_one_or_none()
    if pending and pending.is_valid:
        raise ValueError("A pending invite already exists for this email")

    # Check if the email belongs to an existing member
    user_result = await db.execute(
        select(User).where(User.email == data.email.lower().strip())
    )
    existing_user = user_result.scalar_one_or_none()
    if existing_user and await _already_member(db, existing_user.id, org_id):
        raise ValueError("This user is already a member of the organisation")

    invite = Invite(
        org_id=org_id,
        invited_by=inviter_id,
        email=data.email.lower().strip(),
        role=data.role,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(UTC) + timedelta(days=INVITE_EXPIRY_DAYS),
    )
    db.add(invite)
    await db.flush()

    # Eagerly load relationships for the response
    await db.refresh(invite, ["org", "inviter"])
    return invite


# ── Look up invite by token ───────────────────────────────────────────────────
async def get_invite_public(
    db: AsyncSession, token: str
) -> InvitePublicResponse | None:
    """
    Return minimal invite info for the accept page.
    Safe to call without authentication.
    """
    invite = await _get_invite_by_token(db, token)
    if not invite:
        return None
    return InvitePublicResponse(
        org_name=invite.org.name,
        email=invite.email,
        role=invite.role,
        is_valid=invite.is_valid,
    )


# ── Accept invite ─────────────────────────────────────────────────────────────
async def accept_invite(
    db: AsyncSession, token: str, user: User
) -> Membership:
    """
    Accept an invite and create a membership. Raises ValueError if:
    - the token is invalid or not found
    - the invite is expired or already accepted
    - the invite email doesn't match the authenticated user's email
    - the user is already a member
    """
    invite = await _get_invite_by_token(db, token)

    if not invite:
        raise ValueError("Invite not found")
    if invite.is_expired:
        raise ValueError("This invite has expired")
    if invite.is_accepted:
        raise ValueError("This invite has already been accepted")
    if invite.email != user.email:
        raise ValueError(
            f"This invite was sent to {invite.email}. "
            "Please sign in with that email address to accept it."
        )
    if await _already_member(db, user.id, invite.org_id):
        raise ValueError("You are already a member of this organisation")

    # Mark invite as accepted
    invite.accepted_at = datetime.now(UTC)

    # Create membership
    membership = Membership(
        user_id=user.id,
        org_id=invite.org_id,
        role=invite.role,
    )
    db.add(membership)
    await db.flush()

    return membership


# ── List invites ──────────────────────────────────────────────────────────────
async def list_org_invites(
    db: AsyncSession, org_id: uuid.UUID
) -> list[InviteResponse]:
    """Return all pending (unaccepted, unexpired) invites for an org."""
    result = await db.execute(
        select(Invite)
        .where(
            Invite.org_id == org_id,
            Invite.accepted_at.is_(None),
        )
        .options(joinedload(Invite.org), joinedload(Invite.inviter))
        .order_by(Invite.created_at.desc())
    )
    invites = result.scalars().all()
    return [
        InviteResponse(
            id=inv.id,
            org_id=inv.org_id,
            email=inv.email,
            role=inv.role,
            expires_at=inv.expires_at,
            accepted_at=inv.accepted_at,
            created_at=inv.created_at,
            org_name=inv.org.name,
            invited_by_email=inv.inviter.email,
        )
        for inv in invites
        if not inv.is_expired  # filter expired ones out silently
    ]


# ── Revoke invite ─────────────────────────────────────────────────────────────
async def revoke_invite(
    db: AsyncSession, invite_id: uuid.UUID, org_id: uuid.UUID
) -> None:
    """Delete a pending invite. Raises ValueError if not found."""
    result = await db.execute(
        select(Invite).where(
            Invite.id == invite_id,
            Invite.org_id == org_id,
        )
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise ValueError("Invite not found")
    await db.delete(invite)
    await db.flush()