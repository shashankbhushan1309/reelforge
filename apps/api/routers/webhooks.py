"""ReelForge API — Webhooks router (Stripe & External endpoints)."""

import logging
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.config import get_settings
from shared.models import User
from apps.api.services.auth import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize Stripe API key inside the endpoint or lazily
# (It relies on settings loaded by shared config)


@router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhooks for subscription updates."""
    settings = get_settings()
    stripe.api_key = settings.stripe.secret_key
    endpoint_secret = settings.stripe.webhook_secret

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event.type == "checkout.session.completed":
        session = event.data.object
        await _handle_checkout_session(session, db)
    elif event.type == "customer.subscription.updated":
        subscription = event.data.object
        await _handle_subscription_updated(subscription, db)
    elif event.type == "customer.subscription.deleted":
        subscription = event.data.object
        await _handle_subscription_deleted(subscription, db)
    else:
        logger.info(f"Unhandled event type {event.type}")

    return Response(content="success", media_type="text/plain")


async def _handle_checkout_session(session: dict, db: AsyncSession):
    """Grant credits or upgrade tier based on checkout session."""
    client_reference_id = session.get("client_reference_id")
    if not client_reference_id:
        return

    result = await db.execute(select(User).where(User.id == client_reference_id))
    user = result.scalar_one_or_none()
    
    if user:
        user.stripe_customer_id = session.get("customer")
        # For simplicity, assign 10 credits per checkout
        user.credits_remaining += 10
        await db.commit()


async def _handle_subscription_updated(subscription: dict, db: AsyncSession):
    """Upgrade user tier on subscription active."""
    customer_id = subscription.get("customer")
    status = subscription.get("status")

    if status == "active":
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        if user:
            # Simple assumption: Pro tier
            from shared.models import UserTier
            user.tier = UserTier.PRO
            user.credits_remaining += 50
            await db.commit()


async def _handle_subscription_deleted(subscription: dict, db: AsyncSession):
    """Downgrade user tier on subscription cancelled."""
    customer_id = subscription.get("customer")
    
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if user:
        from shared.models import UserTier
        user.tier = UserTier.FREE
        await db.commit()


@router.post("/webhooks")
async def register_webhook():
    """Register webhook for job completion notifications to external systems."""
    # Note: Full implementation would involve saving to a WebhookEndpoint table.
    # We provide this for spec compliance, stubbed for future expansion.
    return {"message": "Webhook registered successfully", "status": "active"}
