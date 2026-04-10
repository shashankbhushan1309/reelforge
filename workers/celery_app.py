"""Celery application configuration."""

from celery import Celery

from shared.config import get_settings

settings = get_settings()

celery_app = Celery(
    "reelforge",
    broker=settings.redis.url,
    backend=settings.redis.url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "workers.ingest.tasks.*": {"queue": "reelforge:ingest"},
        "workers.scene.tasks.*": {"queue": "reelforge:scene"},
        "workers.scoring.tasks.*": {"queue": "reelforge:score"},
        "workers.audio.tasks.*": {"queue": "reelforge:audio"},
        "workers.dna.tasks.*": {"queue": "reelforge:dna"},
        "workers.blueprint.tasks.*": {"queue": "reelforge:blueprint"},
        "workers.assembly.tasks.*": {"queue": "reelforge:assemble"},
    },
)

# Auto-discover tasks from all worker modules
celery_app.autodiscover_tasks([
    "workers.ingest",
    "workers.scene",
    "workers.scoring",
    "workers.audio",
    "workers.dna",
    "workers.blueprint",
    "workers.assembly",
])
