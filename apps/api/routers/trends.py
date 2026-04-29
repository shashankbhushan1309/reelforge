"""Trends router for Trend Pulse data."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import TrendProfile
from shared.schemas import TrendProfileResponse, PaginatedResponse
from apps.api.services.auth import get_current_user, get_optional_user
from shared.models.database import get_async_session as get_db
from shared.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/trends", response_model=PaginatedResponse)
async def list_trends(
    niche: Optional[str] = Query(None, description="Filter by niche: Travel, Food, Fashion, etc."),
    region: Optional[str] = Query(None, description="Filter by ISO 3166-1 region code"),
    min_energy: Optional[int] = Query(None, ge=1, le=5, description="Minimum energy level"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current trend profiles.

    Filter by niche, region, and energy level.
    Trends are updated every 6 hours by the Trend Pulse service.
    """
    query = select(TrendProfile).where(TrendProfile.is_active == True)

    if niche:
        query = query.where(TrendProfile.niche == niche)
    if region:
        query = query.where(TrendProfile.region == region)
    if min_energy:
        query = query.where(TrendProfile.energy_level >= min_energy)

    query = query.order_by(TrendProfile.virality_score.desc())

    # Count
    from sqlalchemy import func
    count_query = select(func.count(TrendProfile.id)).where(TrendProfile.is_active == True)
    if niche:
        count_query = count_query.where(TrendProfile.niche == niche)
    if region:
        count_query = count_query.where(TrendProfile.region == region)
    if min_energy:
        count_query = count_query.where(TrendProfile.energy_level >= min_energy)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    pages = (total + per_page - 1) // per_page

    offset = (page - 1) * per_page
    query = query.limit(per_page).offset(offset)

    result = await db.execute(query)
    trends = result.scalars().all()

    return PaginatedResponse(
        items=[TrendProfileResponse.model_validate(t) for t in trends],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/trends/niches")
async def list_niches(db: AsyncSession = Depends(get_db)):
    """Get all available niche categories."""
    return {
        "niches": [
            "Travel", "Food", "Fashion", "Fitness", "Lifestyle",
            "Tech", "Comedy", "Beauty", "Music", "Art",
            "Photography", "Gaming", "Education", "Business",
            "Health", "Sports", "Pets", "Nature",
            "Bollywood", "K-beauty", "Cricket",
        ]
    }
