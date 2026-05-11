import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.models.org import Org
from backend.models.membership import Membership
from backend.models.user import User
from backend.schemas.org import OrgCreate, OrgUpdate, OrgWithRoleResponse, MemberResponse, slugify


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _slug_exists(db: AsyncSession, slug: str) -> bool:
    result = await db.execute(select(Org).where(Org.slug == slug))
    return result.scalar_one_or_none() is not None


async def _unique_slug(db: AsyncSession, base_slug: str) -> str:
    """Ensure the slug is unique, appending a number if necessary.
    e.g. 'acme-corp' -> 'acme-corp-2' -> 'acme-corp-3'
    """
    slug = base_slug
    counter = 2
    while await _slug_exists(db, slug):
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


async def _get_membership(
    db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID
) -> Membership | None:
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.org_id == org_id,
        )
    )
    return result.scalar_one_or_none()


# ── Org CRUD ──────────────────────────────────────────────────────────────────
async def create_org(
    db: AsyncSession, data: OrgCreate, owner_id: uuid.UUID
) -> tuple[Org, Membership]:
    """
    Create a new org and make the creator the owner.
    Returns (org, membership) — both flushed but not committed.
    """
    base_slug = data.slug or slugify(data.name)
    slug = await _unique_slug(db, base_slug)

    org = Org(name=data.name.strip(), slug=slug)
    db.add(org)
    await db.flush()

    membership = Membership(user_id=owner_id, org_id=org.id, role="owner")
    db.add(membership)
    await db.flush()

    return org, membership


async def get_org_by_id(db: AsyncSession, org_id: uuid.UUID) -> Org | None:
    result = await db.execute(select(Org).where(Org.id == org_id))
    return result.scalar_one_or_none()


async def get_org_by_slug(db: AsyncSession, slug: str) -> Org | None:
    result = await db.execute(select(Org).where(Org.slug == slug))
    return result.scalar_one_or_none()


async def get_user_orgs(
    db: AsyncSession, user_id: uuid.UUID
) -> list[OrgWithRoleResponse]:
    """Return all orgs the user belongs to, with their role in each."""
    result = await db.execute(
        select(Org, Membership.role)
        .join(Membership, Membership.org_id == Org.id)
        .where(Membership.user_id == user_id)
        .order_by(Org.created_at)
    )
    rows = result.all()
    return [
        OrgWithRoleResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            logo_url=org.logo_url,
            plan=org.plan,
            role=role,
        )
        for org, role in rows
    ]


async def update_org(
    db: AsyncSession, org: Org, data: OrgUpdate
) -> Org:
    if data.name is not None:
        org.name = data.name.strip()
    if data.logo_url is not None:
        org.logo_url = data.logo_url
    await db.flush()
    return org


async def delete_org(db: AsyncSession, org: Org) -> None:
    await db.delete(org)
    await db.flush()


# ── Membership / access ───────────────────────────────────────────────────────
async def get_user_role(
    db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID
) -> str | None:
    """Returns the user's role in the org, or None if they're not a member."""
    membership = await _get_membership(db, user_id, org_id)
    return membership.role if membership else None


async def require_role(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    minimum_role: str,
) -> Membership:
    """
    Returns the membership if the user has at least the required role.
    Raises ValueError otherwise.

    Role hierarchy: owner > admin > member
    """
    hierarchy = ["member", "admin", "owner"]
    membership = await _get_membership(db, user_id, org_id)

    if not membership:
        raise ValueError("Not a member of this organisation")

    if hierarchy.index(membership.role) < hierarchy.index(minimum_role):
        raise ValueError(f"This action requires the '{minimum_role}' role or higher")

    return membership


async def get_org_members(
    db: AsyncSession, org_id: uuid.UUID
) -> list[MemberResponse]:
    """Return all members of an org with their user details."""
    result = await db.execute(
        select(Membership)
        .where(Membership.org_id == org_id)
        .options(joinedload(Membership.user))
        .order_by(Membership.joined_at)
    )
    memberships = result.scalars().all()
    return [
        MemberResponse(
            user_id=m.user_id,
            org_id=m.org_id,
            role=m.role,
            joined_at=m.joined_at,
            email=m.user.email,
            full_name=m.user.full_name,
            avatar_url=m.user.avatar_url,
        )
        for m in memberships
    ]


async def update_member_role(
    db: AsyncSession,
    org_id: uuid.UUID,
    target_user_id: uuid.UUID,
    new_role: str,
) -> Membership:
    """
    Change a member's role. Raises ValueError if:
    - the target user is not a member
    - trying to change the owner's role (ownership transfer not supported yet)
    """
    membership = await _get_membership(db, target_user_id, org_id)
    if not membership:
        raise ValueError("User is not a member of this organisation")
    if membership.role == "owner":
        raise ValueError("Cannot change the owner's role")
    if new_role not in ("admin", "member"):
        raise ValueError("Role must be 'admin' or 'member'")

    membership.role = new_role
    await db.flush()
    return membership


async def remove_member(
    db: AsyncSession,
    org_id: uuid.UUID,
    target_user_id: uuid.UUID,
) -> None:
    """
    Remove a member from an org. Raises ValueError if:
    - the target user is not a member
    - trying to remove the owner
    """
    membership = await _get_membership(db, target_user_id, org_id)
    if not membership:
        raise ValueError("User is not a member of this organisation")
    if membership.role == "owner":
        raise ValueError("Cannot remove the org owner")

    await db.delete(membership)
    await db.flush()