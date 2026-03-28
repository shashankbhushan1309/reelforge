"""ReelForge API — Job orchestration service."""

import logging
from uuid import UUID
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Job, JobStatus, JobMode, MediaItem, MediaSegment, Reel, User
from shared.schemas import JobResponse, JobDetailResponse

logger = logging.getLogger(__name__)


class JobService:
    """Handles job creation, status updates, and queries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_clone_job(
        self,
        user: User,
        inspiration_media_id: UUID,
        user_media_ids: list[UUID],
    ) -> Job:
        """Create a Clone Mode job."""
        # Verify credits
        if user.credits_remaining <= 0:
            raise ValueError("No credits remaining. Please upgrade your plan.")

        job = Job(
            user_id=user.id,
            mode=JobMode.CLONE,
            status=JobStatus.QUEUED,
            inspiration_media_id=inspiration_media_id,
            media_ids=user_media_ids,
        )
        self.db.add(job)

        # Deduct credit
        user.credits_remaining -= 1

        await self.db.commit()
        await self.db.refresh(job)
        logger.info(f"Created clone job {job.id} for user {user.id}")
        return job

    async def create_auto_job(
        self,
        user: User,
        media_ids: list[UUID],
        niche: Optional[str] = None,
        style_preference: Optional[str] = None,
        region: Optional[str] = None,
    ) -> Job:
        """Create an Auto-Create Mode job."""
        if user.credits_remaining <= 0:
            raise ValueError("No credits remaining. Please upgrade your plan.")

        job = Job(
            user_id=user.id,
            mode=JobMode.AUTO,
            status=JobStatus.QUEUED,
            media_ids=media_ids,
            niche=niche,
            style_preference=style_preference,
            region=region,
        )
        self.db.add(job)

        # Deduct credit
        user.credits_remaining -= 1

        await self.db.commit()
        await self.db.refresh(job)
        logger.info(f"Created auto job {job.id} for user {user.id}")
        return job

    async def get_job(self, job_id: UUID, user_id: UUID) -> Optional[Job]:
        """Get a job by ID, scoped to user."""
        result = await self.db.execute(
            select(Job).where(Job.id == job_id, Job.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_jobs(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Job], int]:
        """Get paginated jobs for a user."""
        # Count
        count_result = await self.db.execute(
            select(func.count(Job.id)).where(Job.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # Fetch
        result = await self.db.execute(
            select(Job)
            .where(Job.user_id == user_id)
            .order_by(Job.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        jobs = result.scalars().all()
        return list(jobs), total

    async def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        progress: int = 0,
        error_stage: Optional[str] = None,
        error_message: Optional[str] = None,
        **kwargs,
    ) -> Optional[Job]:
        """Update job status and metadata."""
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return None

        job.status = status
        job.progress = progress
        if error_stage:
            job.error_stage = error_stage
        if error_message:
            job.error_message = error_message

        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)

        await self.db.commit()
        await self.db.refresh(job)
        return job
