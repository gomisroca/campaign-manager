import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.db.session import get_db
from backend.deps import get_current_user
from backend.models.user import User
from backend.services.org_service import get_org_by_id, require_role
from backend.services.stripe_service import (
    PLANS,
    construct_webhook_event,
    create_checkout_session,
    create_portal_session,
    handle_webhook_event,
)

router = APIRouter(tags=["billing"])
settings = get_settings()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_org_or_404(db: AsyncSession, org_id):
    from uuid import UUID
    org = await get_org_by_id(db, UUID(str(org_id)))
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return org


# ── Current billing status ────────────────────────────────────────────────────

@router.get("/orgs/{org_id}/billing")
async def get_billing(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current billing status for an org."""
    from uuid import UUID
    org = await _get_org_or_404(db, org_id)
    try:
        await require_role(db, current_user.id, UUID(org_id), "member")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    return {
        "plan": org.plan,
        "subscription_status": org.subscription_status,
        "stripe_customer_id": org.stripe_customer_id,
        "trial_ends_at": org.trial_ends_at,
    }


# ── Checkout — upgrade to pro ─────────────────────────────────────────────────

@router.post("/orgs/{org_id}/billing/checkout")
async def create_checkout(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe Checkout session for upgrading to Pro.
    Returns a URL to redirect the user to.
    Requires owner role — only the org owner can upgrade billing.
    """
    from uuid import UUID
    org = await _get_org_or_404(db, org_id)
    try:
        await require_role(db, current_user.id, UUID(org_id), "owner")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    if org.plan != "free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organisation is already on a paid plan",
        )

    if not settings.stripe_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured",
        )

    price_id = PLANS.get("pro")
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pro plan price not configured",
        )

    success_url = f"{settings.frontend_url}/billing?success=true"
    cancel_url = f"{settings.frontend_url}/billing?canceled=true"

    url = await create_checkout_session(db, org, price_id, success_url, cancel_url)
    return {"url": url}


# ── Portal — manage existing subscription ─────────────────────────────────────

@router.post("/orgs/{org_id}/billing/portal")
async def create_portal(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe Billing Portal session.
    Returns a URL to redirect the user to.
    Requires owner role.
    """
    from uuid import UUID
    org = await _get_org_or_404(db, org_id)
    try:
        await require_role(db, current_user.id, UUID(org_id), "owner")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    if not org.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found for this organisation",
        )

    return_url = f"{settings.frontend_url}/billing"
    url = await create_portal_session(db, org, return_url)
    return {"url": url}


# ── Webhook ───────────────────────────────────────────────────────────────────

@router.post("/webhooks/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    """
    Receive and process Stripe webhook events.
    This endpoint must NOT require authentication — Stripe calls it directly.
    The payload is verified via the Stripe-Signature header instead.
    """
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    payload = await request.body()

    try:
        event = construct_webhook_event(payload, stripe_signature)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    await handle_webhook_event(db, event)
    return {"received": True}