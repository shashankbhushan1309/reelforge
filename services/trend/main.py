"""ReelForge AI — Trend Pulse Service.

Scheduled service that updates trend profiles every 6 hours.
Fetches social signals and uses Claude to extract structured TrendProfiles.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from apscheduler.schedulers.blocking import BlockingScheduler

from shared.config import get_settings
from shared.models import TrendProfile
from shared.models.database import SyncSessionLocal

logger = logging.getLogger(__name__)


# Sample trending signals for initial data
SEED_TRENDS = [
    {
        "niche": "Travel",
        "trend_name": "Drone Reveal Transition",
        "region": "US",
        "bpm_min": 100,
        "bpm_max": 120,
        "color_palette": ["#FFD700", "#FF6B35", "#1A1A2E"],
        "transition_style": "zoom_burst",
        "text_style": "bold_minimal",
        "energy_level": 4,
        "virality_score": 8.5,
        "estimated_virality_days": 14,
        "audio_description": "Cinematic orchestral with bass drops",
        "visual_description": "Wide drone shots with snap-zoom reveals into ground-level detail",
    },
    {
        "niche": "Fashion",
        "trend_name": "Outfit Whip Pan",
        "region": "US",
        "bpm_min": 120,
        "bpm_max": 140,
        "color_palette": ["#E8D5B7", "#2C2C2C", "#C9A96E"],
        "transition_style": "whip_pan",
        "text_style": "cursive_overlay",
        "energy_level": 5,
        "virality_score": 9.2,
        "estimated_virality_days": 7,
        "audio_description": "Lo-fi beat with sample chops",
        "visual_description": "Quick outfit changes synced to whip pan transitions",
    },
    {
        "niche": "Food",
        "trend_name": "Overhead Pour Slowmo",
        "region": "US",
        "bpm_min": 80,
        "bpm_max": 100,
        "color_palette": ["#8B4513", "#F4A460", "#FFFDD0"],
        "transition_style": "dissolve",
        "text_style": "subtitle_style",
        "energy_level": 3,
        "virality_score": 7.8,
        "estimated_virality_days": 21,
        "audio_description": "ASMR-style ambient with gentle music background",
        "visual_description": "Overhead close-up shots with slow-motion pour and garnish moments",
    },
    {
        "niche": "Fitness",
        "trend_name": "Before/After Split Screen",
        "region": "US",
        "bpm_min": 130,
        "bpm_max": 150,
        "color_palette": ["#FF4444", "#1A1A1A", "#FFFFFF"],
        "transition_style": "hard_cut",
        "text_style": "bold_minimal",
        "energy_level": 5,
        "virality_score": 8.9,
        "estimated_virality_days": 10,
        "audio_description": "High-energy electronic with motivational drops",
        "visual_description": "Side-by-side or sequential before/after transformations with hard cuts on beat",
    },
    {
        "niche": "Tech",
        "trend_name": "Product Unboxing Glitch",
        "region": "US",
        "bpm_min": 110,
        "bpm_max": 130,
        "color_palette": ["#00FF88", "#0D0D0D", "#7B2FBE"],
        "transition_style": "glitch",
        "text_style": "bold_minimal",
        "energy_level": 4,
        "virality_score": 7.5,
        "estimated_virality_days": 12,
        "audio_description": "Futuristic electronic with glitch sound effects",
        "visual_description": "Clean product shots with digital glitch transitions between features",
    },
    {
        "niche": "Bollywood",
        "trend_name": "Dialogue Lip Sync Transition",
        "region": "IN",
        "bpm_min": 90,
        "bpm_max": 120,
        "color_palette": ["#FF6B6B", "#FFD93D", "#6BCB77"],
        "transition_style": "whip_pan",
        "text_style": "subtitle_style",
        "energy_level": 5,
        "virality_score": 9.0,
        "estimated_virality_days": 5,
        "audio_description": "Bollywood movie dialogues with background score",
        "visual_description": "Lip-sync to iconic dialogues with costume/location changes on transitions",
    },
    {
        "niche": "K-beauty",
        "trend_name": "Glass Skin Tutorial",
        "region": "KR",
        "bpm_min": 90,
        "bpm_max": 110,
        "color_palette": ["#FFB6C1", "#FFF0F5", "#E6E6FA"],
        "transition_style": "dissolve",
        "text_style": "cursive_overlay",
        "energy_level": 2,
        "virality_score": 8.2,
        "estimated_virality_days": 30,
        "audio_description": "Soft K-pop or ambient Korean indie",
        "visual_description": "Close-up skincare application with soft lighting and dewy finish reveals",
    },
    {
        "niche": "Comedy",
        "trend_name": "Expectation vs Reality",
        "region": "US",
        "bpm_min": 100,
        "bpm_max": 120,
        "color_palette": ["#FFFFFF", "#000000", "#FF0000"],
        "transition_style": "hard_cut",
        "text_style": "bold_minimal",
        "energy_level": 4,
        "virality_score": 8.7,
        "estimated_virality_days": 8,
        "audio_description": "Trending meme audio with comedic timing beats",
        "visual_description": "Split format showing polished expectation vs chaotic reality",
    },
]


def seed_trends():
    """Seed initial trend profiles."""
    session = SyncSessionLocal()
    try:
        for trend_data in SEED_TRENDS:
            trend = TrendProfile(
                niche=trend_data["niche"],
                trend_name=trend_data["trend_name"],
                region=trend_data["region"],
                bpm_min=trend_data["bpm_min"],
                bpm_max=trend_data["bpm_max"],
                color_palette=trend_data["color_palette"],
                transition_style=trend_data["transition_style"],
                text_style=trend_data["text_style"],
                energy_level=trend_data["energy_level"],
                virality_score=trend_data["virality_score"],
                estimated_virality_days=trend_data["estimated_virality_days"],
                audio_description=trend_data["audio_description"],
                visual_description=trend_data["visual_description"],
                valid_until=datetime.now(timezone.utc) + timedelta(days=trend_data["estimated_virality_days"]),
                is_active=True,
            )
            session.add(trend)

        session.commit()
        logger.info(f"Seeded {len(SEED_TRENDS)} trend profiles")
    except Exception as e:
        logger.error(f"Failed to seed trends: {e}")
        session.rollback()
    finally:
        session.close()


def update_trends():
    """Fetch and update trend profiles (runs every 6 hours)."""
    logger.info("🔄 Updating trend profiles...")

    session = SyncSessionLocal()
    settings = get_settings()

    try:
        # Mark expired trends as inactive
        session.execute(
            TrendProfile.__table__.update()
            .where(TrendProfile.valid_until < datetime.now(timezone.utc))
            .values(is_active=False)
        )
        session.commit()

        # In production, this would scrape social signals and call Claude
        # For now, we ensure seed trends are refreshed
        from sqlalchemy import func
        count = session.execute(
            select(func.count(TrendProfile.id)).where(TrendProfile.is_active == True)
        ).scalar()

        if count == 0:
            seed_trends()

        logger.info(f"✅ Trend update complete. {count} active trends.")

    except Exception as e:
        logger.error(f"Trend update failed: {e}")
        session.rollback()
    finally:
        session.close()


# ── Standalone FastAPI app for the trend service ──

from fastapi import FastAPI
from sqlalchemy import select

trend_app = FastAPI(title="ReelForge Trend Pulse Service", version="0.1.0")


@trend_app.on_event("startup")
async def startup():
    """Seed initial trends and start scheduler."""
    seed_trends()


@trend_app.get("/health")
async def health():
    return {"status": "healthy", "service": "trend-pulse"}


if __name__ == "__main__":
    # Run as standalone scheduler
    logging.basicConfig(level=logging.INFO)
    logger.info("🚀 Starting Trend Pulse Service")

    # Seed initial data
    seed_trends()

    # Start scheduler
    scheduler = BlockingScheduler()
    scheduler.add_job(update_trends, "interval", hours=6)
    logger.info("📅 Scheduled trend updates every 6 hours")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Trend Pulse Service shutting down")
