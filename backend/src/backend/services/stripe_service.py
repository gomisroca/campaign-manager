import uuid

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.org import Org
from backend.services.org_service import get_org_by_id

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

# ── Plans ─────────────────────────────────────────────────────────────────────
# Maps your internal plan names to Stripe price IDs.
# Add more plans here as your product grows.
PLANS = {
    "pro": settings.stripe_pro_price_id,
}

# Maps Stripe subscription statuses to your internal plan name.
# When a subscription becomes active, we set the org to "pro".
# When it's canceled or past_due long enough, we revert to "free".
STATUS_TO_PLAN = {
    "active": "pro",
    "trialing": "pro",
    "past_due": "pro",    # still on pro, just payment failing
    "canceled": "free",
    "unpaid": "free",
    "incomplete_expired": "free",
}


# ── Customer ──────────────────────────────────────────────────────────────────

async def get_or_create_stripe_customer(db: AsyncSession, org: Org) -> str:
    """
    Return the org's Stripe customer ID, creating one if it doesn't exist yet.
    We store the customer ID on the org so we only create it once.
    """
    if org.stripe_customer_id:
        return org.stripe_customer_id

    customer = stripe.Customer.create(
        name=org.name,
        metadata={"org_id": str(org.id)},
    )
    org.stripe_customer_id = customer.id
    await db.flush()
    return customer.id


# ── Checkout session ──────────────────────────────────────────────────────────

async def create_checkout_session(
    db: AsyncSession,
    org: Org,
    price_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Create a Stripe Checkout Session for upgrading to a paid plan.
    Returns the session URL to redirect the user to.
    """
    customer_id = await get_or_create_stripe_customer(db, org)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"org_id": str(org.id)},
        # Pre-fill the customer's email if available
        subscription_data={
            "metadata": {"org_id": str(org.id)},
        },
        # Allow promo codes
        allow_promotion_codes=True,
    )
    return session.url


# ── Billing portal ────────────────────────────────────────────────────────────

async def create_portal_session(
    db: AsyncSession,
    org: Org,
    return_url: str,
) -> str:
    """
    Create a Stripe Billing Portal session so the customer can manage
    their subscription (cancel, update payment method, view invoices).
    Returns the portal URL to redirect the user to.
    """
    customer_id = await get_or_create_stripe_customer(db, org)

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


# ── Webhook handling ──────────────────────────────────────────────────────────

def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """
    Verify the webhook signature and return the parsed event.
    Raises stripe.error.SignatureVerificationError if invalid.
    """
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.stripe_webhook_secret
    )


async def handle_webhook_event(
    db: AsyncSession, event: stripe.Event
) -> None:
    """
    Process a verified Stripe webhook event and update the org accordingly.
    Only handles the events we care about — everything else is ignored.
    """
    event_type = event.type                  # attribute, not ["type"]
    data = event.data.object                 # attribute, not ["data"]["object"]

    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        await _handle_subscription_change(db, data)

    elif event_type == "checkout.session.completed":
        # The subscription events above will handle the actual plan update.
        # This event is useful for one-time setup after a successful checkout.
        pass

    elif event_type == "invoice.payment_failed":
        # Optionally notify the org owner — for now just let the
        # subscription status update handle the downgrade.
        pass


async def _handle_subscription_change(
    db: AsyncSession, subscription
) -> None:
    # StripeObject uses attribute access, not dict .get()
    metadata = subscription.metadata or {}
    org_id_str = metadata.get("org_id") if isinstance(metadata, dict) else getattr(metadata, "org_id", None)

    if not org_id_str:
        return

    try:
        org_id = uuid.UUID(org_id_str)
    except ValueError:
        return

    org = await get_org_by_id(db, org_id)
    if not org:
        return

    status = subscription.status or ""
    org.subscription_status = status
    org.stripe_subscription_id = subscription.id
    org.plan = STATUS_TO_PLAN.get(status, "free")
    await db.flush()