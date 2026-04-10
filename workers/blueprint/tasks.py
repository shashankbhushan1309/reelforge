"""Blueprint generation worker — Claude-powered reel structure planning."""

import json
import logging
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from shared.config import get_settings
from shared.models import (
    Job, JobStatus, JobMode, MediaItem, MediaSegment, TrendProfile,
)
from shared.models.database import SyncSessionLocal

logger = logging.getLogger(__name__)



BLUEPRINT_PROMPT = """You are ReelForge AI's creative director engine. You design precise time-coded reel blueprints that produce Instagram-influencer-quality short-form videos. You understand pacing, visual storytelling, trend alignment, and the psychology of scroll-stopping content.

Generate a reel blueprint for the following inputs.

TARGET DURATION: {target_duration_seconds} seconds
MODE: {mode} (clone | auto)
STYLE DNA: {style_dna_json}
TREND PROFILE: {trend_profile_json}
AVAILABLE MEDIA: {media_manifest_json}

Rules:
- First slot MUST be a hook (0.0–1.2s). Hook clips must have energy_score > 70.
- Beat-aligned cuts: all cut points must land on a beat from the beat_grid.
- Mix video and photo slots. Photos hold for 1.5–2.5s with Ken Burns motion.
- Final slot is always a hold (1.5–3s) for emotional payoff or CTA.
- Vary transition types. Never use the same transition twice in a row.
- Energy should build from mid-energy hook to peak at 60% of reel duration, then resolve.

Return ONLY valid JSON:
{
  "total_duration": <seconds>,
  "slots": [
    {
      "slot_id": <int>,
      "start": <seconds>,
      "end": <seconds>,
      "type": <"clip"|"photo">,
      "media_id": <from available_media>,
      "trim_start": <seconds into source>,
      "trim_end": <seconds into source>,
      "transition_out": <"hard_cut"|"whip_pan"|"zoom_burst"|"dissolve"|"glitch">,
      "ken_burns": <null or {"start_scale":1.0,"end_scale":1.08,"direction":"up|down|left|right"}>,
      "speed_ramp": <null or {"type":"slowmo","factor":0.5}>,
      "mood_role": <"hook"|"build"|"peak"|"resolve"|"cta">
    }
  ],
  "color_grade": <"moody"|"warm_cinematic"|"bright_pop"|"dark_dramatic"|"natural">,
  "text_overlays": [
    {"time": <seconds>, "text": <string>, "style": <"hook"|"mid"|"cta">, "duration": <seconds>}
  ],
  "audio_duck_at": [<seconds where speech detected in source>],
  "creative_rationale": <one sentence explaining the creative approach>
}"""

CAPTION_PROMPT = """You are a viral content strategist who has grown multiple Instagram accounts to 1M+ followers. You write hooks that stop the scroll, captions that drive engagement, and CTAs that convert viewers to followers.

Generate text content for a reel with the following context.

NICHE: {niche}
MOOD: {dominant_mood}
TREND PROFILE: {trend_profile_summary}
TARGET REGION: {region}
REEL DURATION: {duration}s

Return ONLY valid JSON:
{{
  "hook_text": <3–5 word text overlay for first 1.2 seconds>,
  "mid_text": [<0–2 brief overlays for middle of reel. Max 4 words each.>],
  "cta_text": <4–6 word end text>,
  "caption": <Instagram caption. 80–120 words. Hook first sentence. 3–5 hashtag groups.>,
  "hashtags": [<15–20 hashtags>],
  "alt_hooks": [<2 alternative hook texts>]
}}"""


def call_claude(prompt: str, system: str = "") -> str:
    """Call Anthropic Claude API."""
    settings = get_settings()

    if not settings.ai.anthropic_api_key:
        logger.warning("Anthropic API key not set, using mock response")
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ai.anthropic_api_key)

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text
    except Exception as e:
        logger.error(f"Claude API call failed: {e}")
        return None


def build_media_manifest(session, job: Job) -> list[dict]:
    """Build media manifest from scored segments."""
    manifest = []
    media_ids = job.media_ids or []

    for mid in media_ids:
        media_item = session.execute(
            select(MediaItem).where(MediaItem.id == mid)
        ).scalar_one_or_none()

        if not media_item:
            continue

        segments = session.execute(
            select(MediaSegment)
            .where(MediaSegment.media_item_id == mid)
            .order_by(MediaSegment.composite_score.desc().nullslast())
        ).scalars().all()

        for seg in segments:
            manifest.append({
                "media_id": str(seg.id),
                "media_item_id": str(mid),
                "type": media_item.type.value,
                "start_ms": seg.start_ms,
                "end_ms": seg.end_ms,
                "duration_ms": seg.end_ms - seg.start_ms,
                "composite_score": seg.composite_score or 50,
                "mood": seg.mood_tag or "neutral",
                "energy": seg.quality_scores.get("energy", 50) if seg.quality_scores else 50,
                "has_face": seg.face_detected,
                "camera_motion": seg.camera_motion or "handheld",
            })

    return manifest


def generate_mock_blueprint(media_manifest: list, target_duration: float = 15.0) -> dict:
    """Generate a mock blueprint when Claude is unavailable."""
    slots = []
    current_time = 0.0
    transitions = ["hard_cut", "whip_pan", "zoom_burst", "dissolve", "glitch"]

    # Sort by composite score
    sorted_media = sorted(media_manifest, key=lambda x: x["composite_score"], reverse=True)

    slot_id = 0
    for i, media in enumerate(sorted_media[:8]):
        if current_time >= target_duration:
            break

        duration = min(2.5, target_duration - current_time)
        if i == 0:
            duration = min(1.2, duration)  # Hook shot

        slots.append({
            "slot_id": slot_id,
            "start": round(current_time, 2),
            "end": round(current_time + duration, 2),
            "type": media["type"],
            "media_id": media["media_id"],
            "trim_start": media["start_ms"] / 1000,
            "trim_end": min(media["end_ms"] / 1000, media["start_ms"] / 1000 + duration),
            "transition_out": transitions[i % len(transitions)],
            "ken_burns": {"start_scale": 1.0, "end_scale": 1.08, "direction": "up"} if media["type"] == "photo" else None,
            "speed_ramp": None,
            "mood_role": ["hook", "build", "build", "peak", "peak", "resolve", "resolve", "cta"][min(i, 7)],
        })

        current_time += duration
        slot_id += 1

    return {
        "total_duration": round(current_time, 2),
        "slots": slots,
        "color_grade": "warm_cinematic",
        "text_overlays": [
            {"time": 0.0, "text": "Watch this ✨", "style": "hook", "duration": 1.2},
            {"time": current_time - 2.0, "text": "Follow for more", "style": "cta", "duration": 2.0},
        ],
        "audio_duck_at": [],
        "creative_rationale": "Auto-generated blueprint with energy-based clip ordering.",
    }


@shared_task(name="workers.blueprint.tasks.generate_blueprint", bind=True, max_retries=3)
def generate_blueprint(self, job_id: str):
    """Generate reel blueprint using Claude and match media to slots."""
    logger.info(f"[Blueprint] Generating blueprint for job {job_id}")

    session = SyncSessionLocal()
    try:
        job = session.execute(
            select(Job).where(Job.id == UUID(job_id))
        ).scalar_one_or_none()

        if not job:
            return

        job.status = JobStatus.GENERATING_BLUEPRINT
        job.progress = 60
        session.commit()

        # Build media manifest
        media_manifest = build_media_manifest(session, job)

        if not media_manifest:
            logger.error(f"No media found for job {job_id}")
            job.status = JobStatus.FAILED
            job.error_stage = "blueprint"
            job.error_message = "No scored media segments available"
            session.commit()
            return

        # Determine target duration
        total_available = sum(m["duration_ms"] for m in media_manifest) / 1000
        target_duration = min(30, max(8, total_available * 0.6))

        # Get trend profile or style DNA
        style_dna = job.style_dna or {}
        trend_profile = {}

        if job.mode == JobMode.AUTO:
            # Try specified trend_profile_id, else auto-select by niche/region
            tp = None
            if job.trend_profile_id:
                tp = session.execute(
                    select(TrendProfile).where(TrendProfile.id == job.trend_profile_id)
                ).scalar_one_or_none()

            if not tp and job.niche:
                # Auto-select highest virality trend for this niche/region
                query = (
                    select(TrendProfile)
                    .where(
                        TrendProfile.niche == job.niche,
                        TrendProfile.is_active == True,
                    )
                    .order_by(TrendProfile.virality_score.desc().nulls_last())
                    .limit(1)
                )
                if job.region:
                    query = query.where(TrendProfile.region == job.region)
                tp = session.execute(query).scalar_one_or_none()

            if tp:
                trend_profile = {
                    "niche": tp.niche,
                    "bpm_range": [tp.bpm_min, tp.bpm_max],
                    "transition_style": tp.transition_style,
                    "energy_level": tp.energy_level,
                    "color_palette": tp.color_palette,
                }
                # Save the selected trend profile back to job
                job.trend_profile_id = tp.id
                session.commit()

        # Call Claude for blueprint
        prompt = BLUEPRINT_PROMPT.format(
            target_duration_seconds=round(target_duration),
            mode=job.mode.value,
            style_dna_json=json.dumps(style_dna, indent=2),
            trend_profile_json=json.dumps(trend_profile, indent=2),
            media_manifest_json=json.dumps(media_manifest[:20], indent=2),  # Limit to 20 items
        )

        response = call_claude(prompt, system="You are ReelForge AI's creative director engine.")

        if response:
            try:
                # Parse JSON from response
                start = response.find("{")
                end = response.rfind("}") + 1
                blueprint = json.loads(response[start:end])
            except (json.JSONDecodeError, ValueError):
                logger.warning("Failed to parse Claude response, using mock blueprint")
                blueprint = generate_mock_blueprint(media_manifest, target_duration)
        else:
            blueprint = generate_mock_blueprint(media_manifest, target_duration)

        # Store blueprint
        job.blueprint = blueprint
        job.progress = 70
        session.commit()

        # Generate captions
        dominant_mood = "energetic"
        if media_manifest:
            moods = [m.get("mood", "neutral") for m in media_manifest]
            from collections import Counter
            dominant_mood = Counter(moods).most_common(1)[0][0]

        caption_prompt = CAPTION_PROMPT.format(
            niche=job.niche or "Lifestyle",
            dominant_mood=dominant_mood,
            trend_profile_summary=json.dumps(trend_profile),
            region=job.region or "US",
            duration=round(target_duration),
        )

        caption_response = call_claude(caption_prompt)
        if caption_response:
            try:
                start = caption_response.find("{")
                end = caption_response.rfind("}") + 1
                captions = json.loads(caption_response[start:end])
                job.captions = captions
            except (json.JSONDecodeError, ValueError):
                job.captions = {
                    "hook_text": "Watch this ✨",
                    "mid_text": [],
                    "cta_text": "Follow for more",
                    "caption": "Check out this amazing reel! #viral #trending",
                    "hashtags": ["#viral", "#trending", "#reels", "#content"],
                }
        else:
            job.captions = {
                "hook_text": "Watch this ✨",
                "mid_text": [],
                "cta_text": "Follow for more",
                "caption": "Check out this amazing reel! #viral #trending",
                "hashtags": ["#viral", "#trending", "#reels", "#content"],
            }

        job.progress = 75
        session.commit()

        # Push to assembly
        from workers.assembly.tasks import assemble_reel
        assemble_reel.delay(job_id)

        logger.info(f"[Blueprint] Blueprint generated for job {job_id}")

    except Exception as e:
        logger.error(f"[Blueprint] Error: {e}")
        session.rollback()
        if job:
            job.status = JobStatus.FAILED
            job.error_stage = "blueprint"
            job.error_message = str(e)
            session.commit()
        raise self.retry(countdown=60, max_retries=3)
    finally:
        session.close()
