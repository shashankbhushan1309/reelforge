"""Audio analysis worker — BPM, beat grid, and speech detection."""

import json
import logging
import os
import subprocess
import tempfile
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from shared.config import get_settings
from shared.models import MediaItem, MediaType, MediaStatus, Job, JobStatus, JobMode
from shared.models.database import SyncSessionLocal

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_path: str) -> bool:
    """Extract audio track from video using ffmpeg."""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "22050", "-ac", "1",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception:
        return False


def analyze_bpm(audio_path: str) -> dict:
    """Analyze BPM and beat positions using Librosa."""
    try:
        import librosa
        import numpy as np

        y, sr = librosa.load(audio_path, sr=22050)

        # BPM detection
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

        # Convert beat frames to timestamps
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        # Onset detection for more precise beat alignment
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)

        return {
            "bpm": float(tempo) if isinstance(tempo, (int, float)) else float(tempo[0]) if hasattr(tempo, '__len__') else 120.0,
            "beat_times": [float(t) for t in beat_times],
            "onset_times": [float(t) for t in onset_times[:50]],  # Cap at 50 onsets
            "duration": float(librosa.get_duration(y=y, sr=sr)),
        }
    except Exception as e:
        logger.error(f"BPM analysis failed: {e}")
        return {"bpm": 120.0, "beat_times": [], "onset_times": [], "duration": 0}


def detect_speech(audio_path: str) -> dict:
    """Detect speech segments using Whisper."""
    try:
        import whisper

        model = whisper.load_model("base")
        result = model.transcribe(audio_path, fp16=False)

        speech_segments = []
        for seg in result.get("segments", []):
            speech_segments.append({
                "start": float(seg["start"]),
                "end": float(seg["end"]),
                "text": seg.get("text", "").strip(),
            })

        has_speech = len(speech_segments) > 0

        return {
            "has_speech": has_speech,
            "speech_segments": speech_segments,
            "transcript": result.get("text", "").strip(),
            "language": result.get("language", "en"),
        }
    except Exception as e:
        logger.error(f"Speech detection failed: {e}")
        return {"has_speech": False, "speech_segments": [], "transcript": "", "language": "en"}


@shared_task(name="workers.audio.tasks.analyze_audio", bind=True, max_retries=3)
def analyze_audio(self, job_id: str, media_id: str):
    """Analyze audio: BPM detection, speech detection, beat grid generation."""
    logger.info(f"[Audio] Analyzing audio for media {media_id}, job {job_id}")

    session = SyncSessionLocal()
    try:
        media_item = session.execute(
            select(MediaItem).where(MediaItem.id == UUID(media_id))
        ).scalar_one_or_none()

        if not media_item:
            return

        job = session.execute(
            select(Job).where(Job.id == UUID(job_id))
        ).scalar_one_or_none()

        # Skip audio analysis for photos
        if media_item.type == MediaType.PHOTO:
            if job:
                _check_and_advance_pipeline(session, job)
            return

        video_path = os.path.join("/app/uploads", str(media_item.user_id), media_item.filename)

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.wav")

            if os.path.exists(video_path) and extract_audio(video_path, audio_path):
                # BPM analysis
                bpm_data = analyze_bpm(audio_path)

                # Speech detection
                speech_data = detect_speech(audio_path)

                # Store results in job metadata
                if job:
                    audio_analysis = {
                        "media_id": media_id,
                        "bpm": bpm_data["bpm"],
                        "beat_grid": bpm_data["beat_times"],
                        "has_speech": speech_data["has_speech"],
                        "speech_segments": speech_data["speech_segments"],
                        "transcript": speech_data["transcript"],
                        "language": speech_data["language"],
                        "duration": bpm_data["duration"],
                    }

                    # Merge with existing audio analysis
                    existing = job.audio_analysis or {}
                    if "tracks" not in existing:
                        existing["tracks"] = []
                    existing["tracks"].append(audio_analysis)

                    # Use the first video's BPM as the primary beat grid
                    if not job.beat_grid:
                        job.beat_grid = {
                            "bpm": bpm_data["bpm"],
                            "beats": bpm_data["beat_times"],
                        }

                    job.audio_analysis = existing
                    job.progress = 45

            else:
                logger.warning(f"Could not extract audio from {video_path}")

        session.commit()

        # Check if all media items are processed, then advance pipeline
        if job:
            _check_and_advance_pipeline(session, job)

        logger.info(f"[Audio] Completed audio analysis for media {media_id}")

    except Exception as e:
        logger.error(f"[Audio] Error: {e}")
        session.rollback()
        raise self.retry(countdown=30, max_retries=3)
    finally:
        session.close()


def _check_and_advance_pipeline(session, job: Job):
    """Check if all media items are processed and advance to next stage."""
    # Count processed media
    from sqlalchemy import func
    from shared.models import MediaSegment

    processed_count = session.execute(
        select(func.count())
        .select_from(MediaItem)
        .where(
            MediaItem.id.in_(job.media_ids or []),
            MediaItem.status == MediaStatus.READY,
        )
    ).scalar() or 0

    total_media = len(job.media_ids or [])

    if processed_count >= total_media or total_media == 0:
        if job.mode == JobMode.CLONE:
            # clone mode: only advance if DNA is also done
            if job.style_dna:
                job.status = JobStatus.GENERATING_BLUEPRINT
                job.progress = 55
                session.commit()

                from workers.blueprint.tasks import generate_blueprint
                generate_blueprint.delay(str(job.id))
            else:
                logger.info(f"[Audio] Media done for clone job {job.id}, waiting on DNA")
        else:
            job.status = JobStatus.GENERATING_BLUEPRINT
            job.progress = 55
            session.commit()

            from workers.blueprint.tasks import generate_blueprint
            generate_blueprint.delay(str(job.id))
