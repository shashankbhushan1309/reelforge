"""Style DNA Templates router."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, StyleDNATemplate, Job
from shared.schemas import StyleDNATemplateCreate, StyleDNATemplateResponse, PaginatedResponse
from apps.api.services.auth import get_current_user
from shared.models.database import get_async_session as get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dna-templates", response_model=PaginatedResponse)
async def list_templates(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    public_only: bool = Query(False, description="Show only public templates"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List style DNA templates — public templates and user's own."""
    if public_only:
        query = select(StyleDNATemplate).where(StyleDNATemplate.is_public == True)
        count_query = select(func.count(StyleDNATemplate.id)).where(StyleDNATemplate.is_public == True)
    else:
        query = select(StyleDNATemplate).where(
            or_(
                StyleDNATemplate.is_public == True,
                StyleDNATemplate.user_id == user.id,
            )
        )
        count_query = select(func.count(StyleDNATemplate.id)).where(
            or_(
                StyleDNATemplate.is_public == True,
                StyleDNATemplate.user_id == user.id,
            )
        )

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    pages = (total + per_page - 1) // per_page

    offset = (page - 1) * per_page
    query = query.order_by(StyleDNATemplate.usage_count.desc()).limit(per_page).offset(offset)

    result = await db.execute(query)
    templates = result.scalars().all()

    return PaginatedResponse(
        items=[StyleDNATemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post("/dna-templates", response_model=StyleDNATemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: StyleDNATemplateCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a Style DNA from a completed clone job as a reusable template."""
    template = StyleDNATemplate(
        user_id=user.id,
        name=request.name,
        is_public=request.is_public,
    )

    # If job_id provided, copy DNA from job
    if request.job_id:
        result = await db.execute(
            select(Job).where(Job.id == request.job_id, Job.user_id == user.id)
        )
        job = result.scalar_one_or_none()
        if job and job.style_dna:
            dna = job.style_dna
            template.full_dna = dna
            template.cut_pace = dna.get("cut_pace")
            template.color_grade = dna.get("color_grade")
            template.transition_type = dna.get("transition_type")
            template.text_energy = dna.get("text_energy")
            template.bpm = dna.get("bpm")
            template.visual_motion = dna.get("visual_motion")
            template.color_temperature = dna.get("color_temperature")

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return template


@router.delete("/dna-templates/{template_id}")
async def delete_template(
    template_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user's DNA template."""
    result = await db.execute(
        select(StyleDNATemplate).where(
            StyleDNATemplate.id == template_id,
            StyleDNATemplate.user_id == user.id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    await db.delete(template)
    await db.commit()
    return {"message": "Template deleted"}
