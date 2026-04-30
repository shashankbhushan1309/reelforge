"""Ingest worker — media transcoding, thumbnail generation, and storage."""

import json
import logging
import os
import subprocess
import tempfile
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from shared.config import get_settings
from shared.models import MediaItem, MediaSegment, MediaStatus, MediaType, Job, JobStatus
from shared.models.database import SyncSessionLocal

logger = logging.getLogger(__name__)


def get_video_info(filepath: str) -> dict:
    """Extract video metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", filepath,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return json.loads(result.stdout)
    except Exception as e:
        logger.error(f"ffprobe failed: {e}")
        return {}


def transcode_video(input_path: str, output_path: str) -> bool:
    """Transcode video to H.264 MP4 at 1080p / 30fps."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-vf", "scale=1080:-2",
        "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"Transcode failed: {result.stderr}")
            return False
        return True
    except Exception as e:
        logger.error(f"Transcode error: {e}")
        return False


def generate_thumbnails(video_path: str, output_dir: str) -> list[str]:
    """Generate thumbnails at 0.5s, 1s, 2s timestamps."""
    thumbnails = []
    for ts in ["0.5", "1", "2"]:
        thumb_path = os.path.join(output_dir, f"thumb_{ts}s.jpg")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-ss", ts, "-vframes", "1",
            "-vf", "scale=480:-2",
            "-q:v", "2",
            thumb_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and os.path.exists(thumb_path):
                thumbnails.append(thumb_path)
        except Exception:
            pass
    return thumbnails


@shared_task(name="workers.ingest.tasks.process_media", bind=True, max_retries=3)
def process_media(self, job_id: str, media_id: str):
    """Process an uploaded media item: transcode, thumbnail, push to next stage."""
    logger.info(f"[Ingest] Processing media {media_id} for job {job_id}")

    session = SyncSessionLocal()
    try:
        # Get media item
        media_item = session.execute(
            select(MediaItem).where(MediaItem.id == UUID(media_id))
        ).scalar_one_or_none()

        if not media_item:
            logger.error(f"Media item {media_id} not found")
            return

        # Update status
        media_item.status = MediaStatus.PROCESSING
        session.commit()

        # Update job status
        job = session.execute(
            select(Job).where(Job.id == UUID(job_id))
        ).scalar_one_or_none()
        if job and job.status == JobStatus.QUEUED:
            job.status = JobStatus.INGESTING
            job.progress = 10
            session.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            if media_item.type == MediaType.VIDEO:
                # Download from storage (or use local path)
                input_path = os.path.join(tmpdir, "input.mp4")

                # For local development, try local file first
                local_path = os.path.join("/app/uploads", str(media_item.user_id), media_item.filename)
                if os.path.exists(local_path):
                    input_path = local_path
                else:
                    # Download from R2
                    from shared.storage import get_storage
                    storage = get_storage()
                    storage.download_file(media_item.r2_key, input_path)

                # Get video info
                info = get_video_info(input_path)
                if info:
                    streams = info.get("streams", [])
                    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
                    media_item.width = int(video_stream.get("width", 0))
                    media_item.height = int(video_stream.get("height", 0))
                    duration = float(info.get("format", {}).get("duration", 0))
                    media_item.duration_ms = int(duration * 1000)

                # Transcode
                output_path = os.path.join(tmpdir, "transcoded.mp4")
                if transcode_video(input_path, output_path):
                    # Upload transcoded video to R2
                    r2_key = f"processed/{media_item.user_id}/{media_item.id}/video.mp4"
                    try:
                        from shared.storage import get_storage
                        storage = get_storage()
                        storage.upload_file(output_path, r2_key, "video/mp4")
                        media_item.r2_key = r2_key
                    except Exception as e:
                        logger.warning(f"R2 upload skipped (dev mode): {e}")
                        media_item.r2_key = r2_key

                # Generate thumbnails
                thumbs = generate_thumbnails(input_path, tmpdir)
                if thumbs:
                    thumb_r2_key = f"processed/{media_item.user_id}/{media_item.id}/thumb.jpg"
                    try:
                        from shared.storage import get_storage
                        storage = get_storage()
                        storage.upload_file(thumbs[0], thumb_r2_key, "image/jpeg")
                        media_item.r2_thumb_key = thumb_r2_key
                    except Exception:
                        media_item.r2_thumb_key = thumb_r2_key

            elif media_item.type == MediaType.PHOTO:
                # Process photo: resize, analyze
                from PIL import Image

                # For local development, try local file first
                local_path = os.path.join("/app/uploads", str(media_item.user_id), media_item.filename)
                input_path = os.path.join(tmpdir, media_item.filename)
                if os.path.exists(local_path):
                    import shutil
                    shutil.copy2(local_path, input_path)
                elif media_item.r2_key:
                    from shared.storage import get_storage
                    storage = get_storage()
                    storage.download_file(media_item.r2_key, input_path)
                else:
                    raise FileNotFoundError(f"Media not found locally or in R2: {media_item.id}")

                if os.path.exists(input_path):
                    img = Image.open(input_path)
                    media_item.width = img.width
                    media_item.height = img.height

                    # Resize if needed
                    max_dim = 3840  # 4K max
                    resized_path = input_path
                    if max(img.width, img.height) > max_dim:
                        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
                        resized_path = os.path.join(tmpdir, "resized.jpg")
                        img.save(resized_path, "JPEG", quality=95)

                    # Generate thumbnail
                    thumb = img.copy()
                    thumb.thumbnail((480, 480), Image.LANCZOS)
                    thumb_path = os.path.join(tmpdir, "thumb.jpg")
                    thumb.save(thumb_path, "JPEG", quality=85)

                    r2_key = f"processed/{media_item.user_id}/{media_item.id}/resized.jpg"
                    thumb_r2_key = f"processed/{media_item.user_id}/{media_item.id}/thumb.jpg"
                    try:
                        from shared.storage import get_storage
                        storage = get_storage()
                        storage.upload_file(resized_path, r2_key, "image/jpeg")
                        media_item.r2_key = r2_key
                        storage.upload_file(thumb_path, thumb_r2_key, "image/jpeg")
                        media_item.r2_thumb_key = thumb_r2_key
                    except Exception as e:
                        logger.warning(f"R2 upload skipped/failed (dev mode): {e}")
                        media_item.r2_key = r2_key
                        media_item.r2_thumb_key = thumb_r2_key

            # Mark as ready
            media_item.status = MediaStatus.READY
            session.commit()

        # Push to next pipeline stage
        if media_item.type == MediaType.VIDEO:
            # Videos: scene detection → scoring → audio → ...
            from workers.scene.tasks import detect_scenes
            detect_scenes.delay(job_id, media_id)
        else:
            # Photos: skip scene detection, go straight to scoring
            from workers.scoring.tasks import score_media
            score_media.delay(job_id, media_id)

        logger.info(f"[Ingest] Completed processing media {media_id}")

    except Exception as e:
        logger.error(f"[Ingest] Error processing media {media_id}: {e}")
        session.rollback()
        if media_item:
            media_item.status = MediaStatus.FAILED
            session.commit()
        raise self.retry(countdown=30, max_retries=3)
    finally:
        session.close()
