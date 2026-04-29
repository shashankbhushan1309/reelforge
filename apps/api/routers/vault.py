"""Media vault router — user media management."""

import logging
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, MediaItem, MediaSegment, MediaType, MediaStatus
from shared.schemas import MediaItemResponse, MediaSegmentResponse, PaginatedResponse
from apps.api.services.auth import get_current_user
from shared.models.database import get_async_session as get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/vault", response_model=PaginatedResponse)
async def list_vault(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None, description="Filter by type: video or photo"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    mood: Optional[str] = Query(None, description="Filter by mood tag"),
    min_score: Optional[float] = Query(None, description="Minimum composite score"),
    sort_by: str = Query("created_at", description="Sort by: created_at, size_bytes, composite_score"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's media vault with filtering and sorting.

    The media vault contains all uploaded media with quality scores,
    mood tags, and segment information.
    """
    query = select(MediaItem).where(MediaItem.user_id == user.id)
    count_query = select(func.count(MediaItem.id)).where(MediaItem.user_id == user.id)

    # Apply filters
    if type:
        media_type = MediaType.VIDEO if type == "video" else MediaType.PHOTO
        query = query.where(MediaItem.type == media_type)
        count_query = count_query.where(MediaItem.type == media_type)

    if status_filter:
        try:
            ms = MediaStatus(status_filter)
            query = query.where(MediaItem.status == ms)
            count_query = count_query.where(MediaItem.status == ms)
        except ValueError:
            pass

    if mood:
        query = query.where(MediaItem.mood_tags.any(mood))
        count_query = count_query.where(MediaItem.mood_tags.any(mood))

    # Sort
    sort_col = getattr(MediaItem, sort_by, MediaItem.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # Count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    pages = (total + per_page - 1) // per_page

    # Paginate
    offset = (page - 1) * per_page
    query = query.limit(per_page).offset(offset)

    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[MediaItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/vault/{media_id}", response_model=MediaItemResponse)
async def get_media_item(
    media_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single media item with full details."""
    result = await db.execute(
        select(MediaItem).where(MediaItem.id == media_id, MediaItem.user_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found")
    return item


@router.get("/vault/{media_id}/segments", response_model=list[MediaSegmentResponse])
async def get_media_segments(
    media_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all analyzed segments for a media item."""
    # Verify ownership
    result = await db.execute(
        select(MediaItem).where(MediaItem.id == media_id, MediaItem.user_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found")

    result = await db.execute(
        select(MediaSegment)
        .where(MediaSegment.media_item_id == media_id)
        .order_by(MediaSegment.start_ms)
    )
    segments = result.scalars().all()
    return segments


@router.delete("/vault/{media_id}")
async def delete_media_item(
    media_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a media item and its segments."""
    result = await db.execute(
        select(MediaItem).where(MediaItem.id == media_id, MediaItem.user_id == user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found")

    # clean up remote storage
    try:
        from shared.storage import get_storage
        storage = get_storage()
        if item.r2_key:
            storage.delete_file(item.r2_key)
        if item.r2_thumb_key:
            storage.delete_file(item.r2_thumb_key)
    except Exception as e:
        logger.warning(f"R2 cleanup failed for {media_id}: {e}")

    await db.delete(item)
    await db.commit()
    return {"message": "Media item deleted"}
