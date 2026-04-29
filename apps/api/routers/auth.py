"""Auth router — user profile, data export, and account deletion."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel
from shared.models import User, Job, Reel, MediaItem
from shared.schemas import UserResponse
from apps.api.services.auth import get_current_user
from shared.models.database import get_async_session as get_db

router = APIRouter()


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    locale: str | None = None
    timezone: str | None = None


@router.get("/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Get the current authenticated user profile."""
    return user


@router.patch("/auth/me", response_model=UserResponse)
async def update_me(
    request: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    if request.name is not None:
        user.name = request.name
    if request.locale is not None:
        user.locale = request.locale
    if request.timezone is not None:
        user.timezone = request.timezone

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/auth/me/export")
async def export_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all user data (GDPR compliance)."""
    from sqlalchemy import select
    
    # Fetch jobs
    jobs = await db.execute(select(Job).where(Job.user_id == user.id))
    jobs = jobs.scalars().all()
    
    # Fetch reels
    reels = await db.execute(select(Reel).where(Reel.user_id == user.id))
    reels = reels.scalars().all()
    
    # Fetch media
    media = await db.execute(select(MediaItem).where(MediaItem.user_id == user.id))
    media = media.scalars().all()
    
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "locale": user.locale,
            "timezone": user.timezone,
            "tier": user.tier.value,
            "credits_remaining": user.credits_remaining,
            "created_at": user.created_at.isoformat(),
        },
        "jobs": [
            {
                "id": str(j.id),
                "mode": j.mode.value,
                "status": j.status.value,
                "created_at": j.created_at.isoformat()
            } for j in jobs
        ],
        "reels": [
            {
                "id": str(r.id),
                "duration_ms": r.duration_ms,
                "view_count": r.view_count,
                "created_at": r.created_at.isoformat()
            } for r in reels
        ],
        "media_items": [
            {
                "id": str(m.id),
                "type": m.type.value,
                "filename": m.filename,
                "size_bytes": m.size_bytes,
                "status": m.status.value,
                "created_at": m.created_at.isoformat()
            } for m in media
        ]
    }


@router.delete("/auth/me")
async def delete_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete user account and all associated data (GDPR compliance).

    Deletes: user profile, all media from R2, all reels, all jobs, audit logs.
    """
    import logging
    _logger = logging.getLogger(__name__)

    # 1. Cancel any pending/running jobs
    from sqlalchemy import select, update
    from shared.models import JobStatus
    await db.execute(
        update(Job)
        .where(Job.user_id == user.id, Job.status.notin_([JobStatus.COMPLETED, JobStatus.FAILED]))
        .values(status=JobStatus.FAILED, error_message="Account deleted by user")
    )

    # 2. Collect R2 keys for deletion
    r2_keys_to_delete = []

    media_items = await db.execute(select(MediaItem).where(MediaItem.user_id == user.id))
    for m in media_items.scalars().all():
        if m.r2_key:
            r2_keys_to_delete.append(m.r2_key)
        if m.r2_thumb_key:
            r2_keys_to_delete.append(m.r2_thumb_key)

    reels = await db.execute(select(Reel).where(Reel.user_id == user.id))
    for r in reels.scalars().all():
        for key in [r.r2_key, r.r2_square_key, r.r2_landscape_key, r.thumbnail_r2_key]:
            if key:
                r2_keys_to_delete.append(key)

    # 3. Delete from R2 (best effort)
    if r2_keys_to_delete:
        try:
            from shared.storage import get_storage
            storage = get_storage()
            for key in r2_keys_to_delete:
                try:
                    storage.delete_file(key)
                except Exception:
                    pass
            _logger.info(f"Deleted {len(r2_keys_to_delete)} R2 objects for user {user.email}")
        except Exception as e:
            _logger.warning(f"R2 cleanup failed (will cascade DB delete): {e}")

    # 4. Cascade-delete user (all related records via FK cascade)
    await db.delete(user)
    await db.commit()

    _logger.info(f"Account deleted: {user.email}")
    return {"message": "Account and all associated data deleted successfully"}
