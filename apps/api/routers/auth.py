"""ReelForge API — Auth router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel
from shared.models import User, Job, Reel, MediaItem
from shared.schemas import UserResponse
from apps.api.services.auth import get_current_user, get_db

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
    """Delete user account and all associated data (GDPR compliance)."""
    await db.delete(user)
    await db.commit()
    return {"message": "Account deleted successfully"}
