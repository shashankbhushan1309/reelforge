"""Stripe webhooks and external notification hooks."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import get_settings
from shared.models import User, UserTier, Job, JobStatus
from shared.models.database import get_async_session as get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Tier → credits mapping
TIER_CREDITS = {
    UserTier.FREE: 3,
    UserTier.CREATOR: 30,
    UserTier.PRO: 999999,  # Unlimited
    UserTier.STUDIO: 999999,
    UserTier.ENTERPRISE: 999999,
}

# Stripe price_id → tier mapping (built from STRIPE_PRICE_* env vars)
def _build_price_to_tier() -> dict:
    """Build price-to-tier map from settings so it stays in sync with Stripe."""
    settings = get_settings()
    mapping = {}
    if settings.stripe.price_creator:
        mapping[settings.stripe.price_creator] = UserTier.CREATOR
    if settings.stripe.price_pro:
        mapping[settings.stripe.price_pro] = UserTier.PRO
    if settings.stripe.price_studio:
        mapping[settings.stripe.price_studio] = UserTier.STUDIO
    return mapping


def get_price_to_tier() -> dict:
    """Get cached price-to-tier mapping."""
    return _build_price_to_tier()


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events for subscription management."""
    settings = get_settings()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        import stripe
        stripe.api_key = settings.stripe.secret_key

        webhook_secret = settings.stripe.webhook_secret
        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET not configured")
            raise HTTPException(status_code=500, detail="Webhook secret not configured")

        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as e:
        logger.error(f"Stripe webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail=f"Signature verification failed: {str(e)}")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    logger.info(f"Stripe webhook received: {event_type}")

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, data)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(db, data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, data)
    elif event_type == "invoice.payment_succeeded":
        await _handle_payment_succeeded(db, data)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, data)
    else:
        logger.info(f"Unhandled Stripe event: {event_type}")

    return {"status": "ok"}


async def _handle_checkout_completed(db: AsyncSession, data: dict):
    """New subscription checkout completed."""
    customer_id = data.get("customer")
    if not customer_id:
        return

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(f"No user found for Stripe customer {customer_id}")
        return

    # Determine tier from subscription
    subscription_id = data.get("subscription")
    if subscription_id:
        try:
            import stripe
            sub = stripe.Subscription.retrieve(subscription_id)
            price_id = sub["items"]["data"][0]["price"]["id"] if sub.get("items") else None
            tier = get_price_to_tier().get(price_id, UserTier.CREATOR)
        except Exception:
            tier = UserTier.CREATOR
    else:
        tier = UserTier.CREATOR

    user.tier = tier
    user.credits_remaining = TIER_CREDITS.get(tier, 30)
    await db.commit()
    logger.info(f"User {user.email} upgraded to {tier.value} via checkout")


async def _handle_subscription_updated(db: AsyncSession, data: dict):
    """Subscription plan changed (upgrade/downgrade)."""
    customer_id = data.get("customer")
    if not customer_id:
        return

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    # Get new price/tier
    items = data.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")
        new_tier = get_price_to_tier().get(price_id, user.tier)

        if new_tier != user.tier:
            old_tier = user.tier
            user.tier = new_tier
            user.credits_remaining = TIER_CREDITS.get(new_tier, 30)
            await db.commit()
            logger.info(f"User {user.email} changed tier: {old_tier.value} → {new_tier.value}")


async def _handle_subscription_deleted(db: AsyncSession, data: dict):
    """Subscription cancelled — downgrade to free."""
    customer_id = data.get("customer")
    if not customer_id:
        return

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.tier = UserTier.FREE
    user.credits_remaining = TIER_CREDITS[UserTier.FREE]
    await db.commit()
    logger.info(f"User {user.email} downgraded to free (subscription cancelled)")


async def _handle_payment_succeeded(db: AsyncSession, data: dict):
    """Recurring payment succeeded — reset credits."""
    customer_id = data.get("customer")
    if not customer_id:
        return

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.credits_remaining = TIER_CREDITS.get(user.tier, 3)
    await db.commit()
    logger.info(f"Credits reset for {user.email} ({user.tier.value}): {user.credits_remaining}")


async def _handle_payment_failed(db: AsyncSession, data: dict):
    """Payment failed — log but don't immediately downgrade."""
    customer_id = data.get("customer")
    logger.warning(f"Payment failed for Stripe customer {customer_id}")


@router.post("/webhooks/job-complete")
async def job_complete_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """External webhook for job completion notifications."""
    body = await request.json()
    job_id = body.get("job_id")
    status_str = body.get("status")

    if not job_id:
        raise HTTPException(status_code=400, detail="job_id required")

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "progress": job.progress,
    }
