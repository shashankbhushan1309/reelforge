"""ReelForge API — Reels router for reel retrieval and regeneration."""

import logging
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, Reel, Job, JobStatus, JobMode
from shared.schemas import ReelResponse, RegenerateRequest, JobResponse
from shared.queue import get_queue, QUEUE_ASSEMBLE
from shared.config import get_settings
from apps.api.services.auth import get_current_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter()


def build_reel_response(reel: Reel) -> ReelResponse:
    """Build reel response with CDN URLs."""
    settings = get_settings()
    base_url = settings.r2.public_url

    return ReelResponse(
        id=reel.id,
        job_id=reel.job_id,
        r2_key=reel.r2_key,
        r2_square_key=reel.r2_square_key,
        r2_landscape_key=reel.r2_landscape_key,
        duration_ms=reel.duration_ms,
        thumbnail_url=f"{base_url}/{reel.thumbnail_r2_key}" if reel.thumbnail_r2_key else None,
        share_token=reel.share_token,
        view_count=reel.view_count,
        download_count=reel.download_count,
        captions=reel.captions,
        download_url=f"{base_url}/{reel.r2_key}" if reel.r2_key else None,
        square_download_url=f"{base_url}/{reel.r2_square_key}" if reel.r2_square_key else None,
        landscape_download_url=f"{base_url}/{reel.r2_landscape_key}" if reel.r2_landscape_key else None,
        created_at=reel.created_at,
    )


@router.get("/reels/{reel_id}", response_model=ReelResponse)
async def get_reel(
    reel_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a completed reel with CDN URLs for all format variants."""
    result = await db.execute(
        select(Reel).where(Reel.id == reel_id, Reel.user_id == user.id)
    )
    reel = result.scalar_one_or_none()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")

    return build_reel_response(reel)


@router.get("/reels/share/{share_token}", response_model=ReelResponse)
async def get_shared_reel(
    share_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a reel by share token (public, no auth required)."""
    result = await db.execute(
        select(Reel).where(Reel.share_token == share_token)
    )
    reel = result.scalar_one_or_none()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")

    # Increment view count
    reel.view_count += 1
    await db.commit()

    return build_reel_response(reel)


@router.post("/reels/{reel_id}/regenerate", response_model=JobResponse)
async def regenerate_reel(
    reel_id: UUID,
    request: RegenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate a reel with different creative choices.

    Each regeneration produces a meaningfully different output using
    different slot assignments, color grade, transitions, and emotional arc.
    """
    # Find original reel and its job
    result = await db.execute(
        select(Reel).where(Reel.id == reel_id, Reel.user_id == user.id)
    )
    reel = result.scalar_one_or_none()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")

    # Get original job
    result = await db.execute(select(Job).where(Job.id == reel.job_id))
    original_job = result.scalar_one_or_none()
    if not original_job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original job not found")

    # Check credits
    if user.credits_remaining <= 0:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="No credits remaining")

    # Create new job with ALL data from original
    new_job = Job(
        user_id=user.id,
        mode=original_job.mode,
        status=JobStatus.GENERATING_BLUEPRINT,
        inspiration_media_id=original_job.inspiration_media_id,
        media_ids=original_job.media_ids,
        style_dna=original_job.style_dna,
        trend_profile_id=original_job.trend_profile_id,
        niche=original_job.niche,
        region=original_job.region,
        style_preference=original_job.style_preference,
        beat_grid=original_job.beat_grid,
        audio_analysis=original_job.audio_analysis,
        progress=55,
    )
    db.add(new_job)
    user.credits_remaining -= 1
    await db.commit()
    await db.refresh(new_job)

    # Dispatch directly to blueprint worker (Celery)
    try:
        from workers.blueprint.tasks import generate_blueprint
        generate_blueprint.delay(str(new_job.id))
    except Exception as e:
        logger.warning(f"Celery dispatch failed, using queue fallback: {e}")
        queue = get_queue()
        queue.push(QUEUE_ASSEMBLE, {
            "job_id": str(new_job.id),
            "regeneration_number": request.regeneration_number,
        })

    return new_job


@router.post("/reels/{reel_id}/share")
async def create_share_link(
    reel_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a public share link for a reel."""
    result = await db.execute(
        select(Reel).where(Reel.id == reel_id, Reel.user_id == user.id)
    )
    reel = result.scalar_one_or_none()
    if not reel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reel not found")

    if not reel.share_token:
        reel.share_token = secrets.token_urlsafe(32)
        await db.commit()

    settings = get_settings()
    share_url = f"{settings.app.api_base_url}/share/{reel.share_token}"

    return {"share_url": share_url, "share_token": reel.share_token}
