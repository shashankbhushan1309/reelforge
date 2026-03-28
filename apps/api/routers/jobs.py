"""ReelForge API — Jobs router for Clone and Auto-Create modes."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, Job, JobStatus
from shared.schemas import (
    CloneJobRequest,
    AutoJobRequest,
    JobResponse,
    JobDetailResponse,
    BlueprintResponse,
    PaginatedResponse,
)
from shared.queue import get_queue, QUEUE_INGEST, QUEUE_DNA
from apps.api.services.auth import get_current_user, get_db
from apps.api.services.job_service import JobService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/jobs/clone", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_clone_job(
    request: CloneJobRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a Clone Mode job.

    Clone mode extracts the Style DNA from an inspiration reel and
    recreates the same style with the user's own media.
    """
    service = JobService(db)
    try:
        job = await service.create_clone_job(
            user=user,
            inspiration_media_id=request.inspiration_media_id,
            user_media_ids=request.user_media_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))

    # Push to ingest queue for user media, and DNA queue for inspiration
    queue = get_queue()
    queue.push(QUEUE_DNA, {
        "job_id": str(job.id),
        "media_id": str(request.inspiration_media_id),
        "mode": "clone",
    })
    for media_id in request.user_media_ids:
        queue.push(QUEUE_INGEST, {
            "job_id": str(job.id),
            "media_id": str(media_id),
        })

    return job


@router.post("/jobs/auto", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_auto_job(
    request: AutoJobRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start an Auto-Create Mode job.

    Auto-Create mode analyzes raw media, picks the best clips,
    maps them to a trending reel structure, and produces a finished reel.
    """
    service = JobService(db)
    try:
        job = await service.create_auto_job(
            user=user,
            media_ids=request.media_ids,
            niche=request.niche,
            style_preference=request.style_preference,
            region=request.region,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))

    # Push all media to ingest queue
    queue = get_queue()
    for media_id in request.media_ids:
        queue.push(QUEUE_INGEST, {
            "job_id": str(job.id),
            "media_id": str(media_id),
        })

    return job


@router.get("/jobs", response_model=PaginatedResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all jobs for the current user."""
    service = JobService(db)
    offset = (page - 1) * per_page
    jobs, total = await service.get_user_jobs(user.id, limit=per_page, offset=offset)
    pages = (total + per_page - 1) // per_page

    return PaginatedResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll job status. Returns status, progress %, and current stage."""
    service = JobService(db)
    job = await service.get_job(job_id, user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/blueprint", response_model=BlueprintResponse)
async def get_blueprint(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the blueprint preview for a job.

    Returns the slot manifest with media assignments.
    Available after the blueprint stage completes.
    """
    service = JobService(db)
    job = await service.get_job(job_id, user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if not job.blueprint:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Blueprint not yet generated. Current status: " + job.status.value,
        )

    return BlueprintResponse(**job.blueprint)
