"""ReelForge AI — Scene Detection Worker.

Runs PySceneDetect to segment videos into individual scenes.
Each segment is stored in media_segments with start/end timestamps.
"""

import logging
import os
import tempfile
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from shared.models import MediaItem, MediaSegment, MediaType, Job, JobStatus
from shared.models.database import SyncSessionLocal

logger = logging.getLogger(__name__)

SCENE_THRESHOLD = 27.0  # Configurable per content type


def run_scene_detection(video_path: str, threshold: float = SCENE_THRESHOLD) -> list[dict]:
    """Run PySceneDetect content-aware scene detection."""
    try:
        from scenedetect import detect, ContentDetector

        scene_list = detect(video_path, ContentDetector(threshold=threshold))

        segments = []
        for i, (start, end) in enumerate(scene_list):
            start_ms = int(start.get_seconds() * 1000)
            end_ms = int(end.get_seconds() * 1000)
            duration_ms = end_ms - start_ms

            # Skip very short segments (< 500ms)
            if duration_ms < 500:
                continue

            segments.append({
                "index": i,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "duration_ms": duration_ms,
            })

        # If no scenes detected (very short clip), treat as single segment
        if not segments:
            import subprocess
            import json
            probe_cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", video_path,
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
            info = json.loads(result.stdout)
            duration = float(info.get("format", {}).get("duration", 3))
            segments.append({
                "index": 0,
                "start_ms": 0,
                "end_ms": int(duration * 1000),
                "duration_ms": int(duration * 1000),
            })

        return segments

    except Exception as e:
        logger.error(f"Scene detection failed: {e}")
        raise


@shared_task(name="workers.scene.tasks.detect_scenes", bind=True, max_retries=3)
def detect_scenes(self, job_id: str, media_id: str):
    """Detect scenes in a video and store segment manifest."""
    logger.info(f"[Scene] Detecting scenes in media {media_id} for job {job_id}")

    session = SyncSessionLocal()
    try:
        media_item = session.execute(
            select(MediaItem).where(MediaItem.id == UUID(media_id))
        ).scalar_one_or_none()

        if not media_item or media_item.type != MediaType.VIDEO:
            logger.info(f"Media {media_id} is not a video, skipping scene detection")
            # For photos, push directly to scoring
            from workers.scoring.tasks import score_media
            score_media.delay(job_id, media_id)
            return

        # Update job status
        job = session.execute(
            select(Job).where(Job.id == UUID(job_id))
        ).scalar_one_or_none()
        if job:
            job.status = JobStatus.ANALYSING
            job.progress = 25
            session.commit()

        # Get video file path
        local_path = os.path.join("/app/uploads", str(media_item.user_id), media_item.filename)

        with tempfile.TemporaryDirectory() as tmpdir:
            if os.path.exists(local_path):
                video_path = local_path
            elif media_item.r2_key:
                video_path = os.path.join(tmpdir, "input.mp4")
                try:
                    from shared.storage import get_storage
                    get_storage().download_file(media_item.r2_key, video_path)
                except Exception as e:
                    logger.warning(f"Could not download from R2: {e}")
                    return
            else:
                logger.warning(f"File not found locally or in R2 for {media_id}")
                return

            # Run scene detection
            segments = run_scene_detection(video_path)
            logger.info(f"[Scene] Found {len(segments)} segments in media {media_id}")

        # Store segments in database
        for seg in segments:
            segment = MediaSegment(
                media_item_id=media_item.id,
                start_ms=seg["start_ms"],
                end_ms=seg["end_ms"],
            )
            session.add(segment)

        session.commit()

        # Push to scoring queue
        from workers.scoring.tasks import score_media
        score_media.delay(job_id, media_id)

        logger.info(f"[Scene] Completed scene detection for media {media_id}")

    except Exception as e:
        logger.error(f"[Scene] Error: {e}")
        session.rollback()
        raise self.retry(countdown=30, max_retries=3)
    finally:
        session.close()
