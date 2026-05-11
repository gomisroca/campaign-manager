import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.deps import get_current_user
from backend.models.user import User
from backend.schemas.invite import InviteAccept, InviteCreate, InvitePublicResponse, InviteResponse
from backend.services.invite_service import (
    accept_invite,
    create_invite,
    get_invite_public,
    list_org_invites,
    revoke_invite,
)
from backend.services.email_service import send_invite_email
from backend.services.org_service import get_org_by_id, require_role
from backend.config import get_settings

settings = get_settings()
router = APIRouter(tags=["invites"])


# ── Org-scoped invite endpoints ───────────────────────────────────────────────
@router.post(
    "/orgs/{org_id}/invites",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    org_id: uuid.UUID,
    data: InviteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send an invite to join an org. Requires admin or owner role."""
    org = await get_org_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

    try:
        await require_role(db, current_user.id, org_id, "admin")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    try:
        invite = await create_invite(db, org_id, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    send_invite_email(
        to=invite.email,
        org_name=invite.org.name,
        inviter_email=invite.inviter.email,
        role=invite.role,
        invite_url=f"{settings.invite_url}?token={invite.token}",
    )

    return InviteResponse(
        id=invite.id,
        org_id=invite.org_id,
        email=invite.email,
        role=invite.role,
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
        created_at=invite.created_at,
        org_name=invite.org.name,
        invited_by_email=invite.inviter.email,
    )


@router.get("/orgs/{org_id}/invites", response_model=list[InviteResponse])
async def list_invites(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List pending invites for an org. Requires admin or owner role."""
    org = await get_org_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

    try:
        await require_role(db, current_user.id, org_id, "admin")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    return await list_org_invites(db, org_id)


@router.delete("/orgs/{org_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke(
    org_id: uuid.UUID,
    invite_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a pending invite. Requires admin or owner role."""
    try:
        await require_role(db, current_user.id, org_id, "admin")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    try:
        await revoke_invite(db, invite_id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Token-based endpoints (no org_id needed) ──────────────────────────────────
@router.get("/invites/{token}", response_model=InvitePublicResponse)
async def get_invite(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Look up an invite by token. No authentication required.
    Used by the frontend accept page to show invite details before login.
    """
    invite = await get_invite_public(db, token)
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    return invite


@router.post("/invites/accept", status_code=status.HTTP_200_OK)
async def accept(
    data: InviteAccept,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept an invite. User must be authenticated with the invited email address.
    Returns the org the user just joined.
    """
    try:
        membership = await accept_invite(db, data.token, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"org_id": str(membership.org_id), "role": membership.role}