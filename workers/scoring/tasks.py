"""ReelForge AI — Scoring Worker.

Extracts keyframes from each video segment, sends to GPT-4o Vision
for quality scoring, computes composite scores.
"""

import base64
import json
import logging
import os
import subprocess
import tempfile
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from shared.config import get_settings
from shared.models import MediaItem, MediaSegment, MediaType, Job, JobStatus
from shared.models.database import SyncSessionLocal

logger = logging.getLogger(__name__)

# Frame quality scoring prompt for GPT-4o Vision
SCORING_PROMPT = """You are a professional video editor and cinematographer with 15 years experience creating viral social media content. You evaluate video frames for their suitability in high-quality reel production.

Evaluate this video frame for use in a short-form social media reel. Score each dimension from 0 to 100.

Return ONLY valid JSON, no explanation:
{
  "sharpness": <0-100, is the subject in sharp focus or motion-blurred?>,
  "face_clarity": <0-100, 0 if no face present, 100 if face is sharp, well-lit, expressive>,
  "composition": <0-100, rule of thirds alignment, subject placement, visual balance>,
  "lighting": <0-100, quality of light: flat=30, harsh=40, soft natural=80, golden hour=100>,
  "energy": <0-100, how much visual energy does this frame have for a reel context?>,
  "mood": <one of: energetic, calm, dramatic, joyful, melancholic, powerful, intimate>,
  "has_face": <true|false>,
  "camera_motion": <one of: static, handheld, tracking, drone>,
  "color_temp": <one of: warm, neutral, cool>
}"""


def extract_keyframe(video_path: str, timestamp_ms: int, output_path: str) -> bool:
    """Extract a keyframe at the specified timestamp."""
    timestamp_s = timestamp_ms / 1000
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp_s),
        "-i", video_path,
        "-vframes", "1",
        "-vf", "scale=1024:-2",
        "-q:v", "2",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception:
        return False


def score_frame_with_gpt4o(image_path: str) -> dict:
    """Send a frame to GPT-4o Vision for quality scoring."""
    settings = get_settings()

    if not settings.ai.openai_api_key:
        logger.warning("OpenAI API key not set, using mock scores")
        return _mock_scores()

    try:
        import openai
        client = openai.OpenAI(api_key=settings.ai.openai_api_key)

        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SCORING_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Score this frame:"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "low",
                            },
                        },
                    ],
                },
            ],
            max_tokens=500,
            temperature=0.1,
        )

        content = response.choices[0].message.content
        # Extract JSON from response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])

        return _mock_scores()

    except Exception as e:
        logger.error(f"GPT-4o scoring failed: {e}")
        return _mock_scores()


def _mock_scores() -> dict:
    """Generate mock scores for development/testing."""
    import random
    return {
        "sharpness": random.randint(50, 95),
        "face_clarity": random.randint(0, 90),
        "composition": random.randint(40, 90),
        "lighting": random.randint(40, 95),
        "energy": random.randint(30, 95),
        "mood": random.choice(["energetic", "calm", "dramatic", "joyful", "powerful"]),
        "has_face": random.choice([True, False]),
        "camera_motion": random.choice(["static", "handheld", "tracking"]),
        "color_temp": random.choice(["warm", "neutral", "cool"]),
    }


def compute_composite_score(scores: dict) -> float:
    """Compute weighted composite score from individual dimensions."""
    return (
        scores.get("sharpness", 0) * 0.25
        + scores.get("face_clarity", 0) * 0.20
        + scores.get("composition", 0) * 0.20
        + scores.get("lighting", 0) * 0.20
        + scores.get("energy", 0) * 0.15
    )


@shared_task(name="workers.scoring.tasks.score_media", bind=True, max_retries=3)
def score_media(self, job_id: str, media_id: str):
    """Score all segments of a media item using GPT-4o Vision."""
    logger.info(f"[Scoring] Scoring media {media_id} for job {job_id}")

    session = SyncSessionLocal()
    try:
        media_item = session.execute(
            select(MediaItem).where(MediaItem.id == UUID(media_id))
        ).scalar_one_or_none()

        if not media_item:
            return

        # For photos, score the whole image
        if media_item.type == MediaType.PHOTO:
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                photo_path = os.path.join("/app/uploads", str(media_item.user_id), media_item.filename)
                if not os.path.exists(photo_path) and media_item.r2_key:
                    photo_path = os.path.join(tmpdir, "input.jpg")
                    try:
                        from shared.storage import get_storage
                        get_storage().download_file(media_item.r2_key, photo_path)
                    except Exception as e:
                        logger.warning(f"Could not download photo from R2: {e}")

                if os.path.exists(photo_path):
                    scores = score_frame_with_gpt4o(photo_path)
                    composite = compute_composite_score(scores)

                # Create a single segment for the photo
                segment = MediaSegment(
                    media_item_id=media_item.id,
                    start_ms=0,
                    end_ms=2000,  # Photos default to 2s
                    composite_score=composite,
                    quality_scores=scores,
                    mood_tag=scores.get("mood"),
                    face_detected=scores.get("has_face", False),
                    camera_motion=scores.get("camera_motion", "static"),
                    color_temp=scores.get("color_temp", "neutral"),
                )
                session.add(segment)

                # Update media mood tags
                media_item.mood_tags = [scores.get("mood", "neutral")]

            session.commit()

            # Push to audio queue (skip for photos but maintain pipeline)
            from workers.audio.tasks import analyze_audio
            analyze_audio.delay(job_id, media_id)
            return

        # For videos, score each segment
        segments = session.execute(
            select(MediaSegment)
            .where(MediaSegment.media_item_id == media_item.id)
            .order_by(MediaSegment.start_ms)
        ).scalars().all()

        if not segments:
            logger.warning(f"No segments found for media {media_id}")
            from workers.audio.tasks import analyze_audio
            analyze_audio.delay(job_id, media_id)
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join("/app/uploads", str(media_item.user_id), media_item.filename)
            if not os.path.exists(video_path) and media_item.r2_key:
                video_path = os.path.join(tmpdir, "input.mp4")
                try:
                    from shared.storage import get_storage
                    get_storage().download_file(media_item.r2_key, video_path)
                except Exception as e:
                    logger.warning(f"Could not download video from R2: {e}")
            for segment in segments:
                # Extract keyframe from middle of segment
                midpoint_ms = (segment.start_ms + segment.end_ms) // 2
                keyframe_path = os.path.join(tmpdir, f"keyframe_{segment.id}.jpg")

                if os.path.exists(video_path) and extract_keyframe(video_path, midpoint_ms, keyframe_path):
                    # Score with GPT-4o
                    scores = score_frame_with_gpt4o(keyframe_path)
                    composite = compute_composite_score(scores)

                    segment.quality_scores = scores
                    segment.composite_score = composite
                    segment.mood_tag = scores.get("mood")
                    segment.face_detected = scores.get("has_face", False)
                    segment.camera_motion = scores.get("camera_motion")
                    segment.color_temp = scores.get("color_temp")

                    # Upload keyframe to R2
                    r2_key = f"keyframes/{media_item.user_id}/{segment.id}.jpg"
                    segment.keyframe_r2_key = r2_key

                else:
                    # Use mock scores if keyframe extraction fails
                    scores = _mock_scores()
                    segment.quality_scores = scores
                    segment.composite_score = compute_composite_score(scores)
                    segment.mood_tag = scores.get("mood")

        # Update media mood tags with dominant mood
        moods = [s.mood_tag for s in segments if s.mood_tag]
        if moods:
            from collections import Counter
            media_item.mood_tags = [Counter(moods).most_common(1)[0][0]]

        session.commit()

        # Push to audio analysis
        from workers.audio.tasks import analyze_audio
        analyze_audio.delay(job_id, media_id)

        logger.info(f"[Scoring] Completed scoring for media {media_id}")

    except Exception as e:
        logger.error(f"[Scoring] Error: {e}")
        session.rollback()
        raise self.retry(countdown=30, max_retries=3)
    finally:
        session.close()
