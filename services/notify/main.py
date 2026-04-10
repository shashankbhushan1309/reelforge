"""Notification service — job completion alerts."""

import json
import logging
from uuid import UUID

from shared.config import get_settings
from shared.models import Job, Reel, User, JobStatus
from shared.models.database import SyncSessionLocal
from shared.queue import get_queue, QUEUE_NOTIFY
from sqlalchemy import select

logger = logging.getLogger(__name__)


def send_notification(job_id: str, notification_type: str = "reel_ready"):
    """Send notification to user about job completion."""
    session = SyncSessionLocal()
    try:
        job = session.execute(
            select(Job).where(Job.id == UUID(job_id))
        ).scalar_one_or_none()

        if not job:
            return

        user = session.execute(
            select(User).where(User.id == job.user_id)
        ).scalar_one_or_none()

        if not user:
            return

        if notification_type == "reel_ready":
            reel = session.execute(
                select(Reel).where(Reel.job_id == job.id)
            ).scalar_one_or_none()

            if reel:
                logger.info(f"Notification: Reel ready for user {user.email} (reel: {reel.id})")

                # In production: send email, push notification, webhooks
                # email_service.send(
                #     to=user.email,
                #     subject="Your reel is ready! 🎬",
                #     body=f"Your ReelForge reel is ready to download."
                # )

        elif notification_type == "job_failed":
            logger.info(f"Notification: Job failed for user {user.email} (job: {job.id})")

    except Exception as e:
        logger.error(f"Notification error: {e}")
    finally:
        session.close()


def process_notification_queue():
    """Process pending notifications from the queue."""
    queue = get_queue()
    while True:
        message = queue.pop(QUEUE_NOTIFY, timeout=5)
        if message:
            send_notification(
                job_id=message.get("job_id"),
                notification_type=message.get("type", "reel_ready"),
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Notification Service")
    process_notification_queue()
