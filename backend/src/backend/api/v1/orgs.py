import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.deps import get_current_user
from backend.models.user import User
from backend.schemas.org import (
    MemberResponse,
    OrgCreate,
    OrgResponse,
    OrgUpdate,
    OrgWithRoleResponse,
)
from backend.services.org_service import (
    create_org,
    delete_org,
    get_org_by_id,
    get_org_members,
    get_user_orgs,
    remove_member,
    require_role,
    update_member_role,
    update_org,
)

router = APIRouter(prefix="/orgs", tags=["orgs"])


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _get_org_or_404(db: AsyncSession, org_id: uuid.UUID):
    org = await get_org_by_id(db, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return org


# ── Org endpoints ─────────────────────────────────────────────────────────────
@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create(
    data: OrgCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new org. The authenticated user becomes the owner."""
    org, _ = await create_org(db, data, owner_id=current_user.id)
    return OrgResponse.model_validate(org)


@router.get("", response_model=list[OrgWithRoleResponse])
async def list_orgs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all orgs the current user belongs to, with their role in each."""
    return await get_user_orgs(db, current_user.id)


@router.get("/{org_id}", response_model=OrgResponse)
async def get_org(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single org. User must be a member."""
    org = await _get_org_or_404(db, org_id)
    try:
        await require_role(db, current_user.id, org_id, "member")
    except ValueError:
        # Return 404 rather than 403 — don't reveal the org exists to non-members
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return OrgResponse.model_validate(org)


@router.patch("/{org_id}", response_model=OrgResponse)
async def patch_org(
    org_id: uuid.UUID,
    data: OrgUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update org name or logo. Requires admin or owner role."""
    org = await _get_org_or_404(db, org_id)
    try:
        await require_role(db, current_user.id, org_id, "admin")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return OrgResponse.model_validate(await update_org(db, org, data))


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an org and all its data. Requires owner role."""
    org = await _get_org_or_404(db, org_id)
    try:
        await require_role(db, current_user.id, org_id, "owner")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    await delete_org(db, org)


# ── Member endpoints ──────────────────────────────────────────────────────────
@router.get("/{org_id}/members", response_model=list[MemberResponse])
async def list_members(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all members of an org. Requires member role."""
    await _get_org_or_404(db, org_id)
    try:
        await require_role(db, current_user.id, org_id, "member")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return await get_org_members(db, org_id)


@router.patch("/{org_id}/members/{user_id}", response_model=MemberResponse)
async def update_role(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change a member's role. Requires admin or owner role."""
    await _get_org_or_404(db, org_id)
    try:
        await require_role(db, current_user.id, org_id, "admin")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    new_role = data.get("role")
    if not new_role:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="'role' is required")

    try:
        membership = await update_member_role(db, org_id, user_id, new_role)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    members = await get_org_members(db, org_id)
    return next(m for m in members if m.user_id == membership.user_id)


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from an org. Requires admin or owner role, or self-removal."""
    await _get_org_or_404(db, org_id)

    # Allow members to remove themselves
    is_self = current_user.id == user_id
    if not is_self:
        try:
            await require_role(db, current_user.id, org_id, "admin")
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    try:
        await remove_member(db, org_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))