"""ReelForge AI — Redis queue helpers for inter-service communication."""

import json
import logging
from typing import Any, Optional

import redis

from shared.config import get_settings

logger = logging.getLogger(__name__)

# Queue names
QUEUE_INGEST = "reelforge:ingest"
QUEUE_SCENE = "reelforge:scene"
QUEUE_SCORE = "reelforge:score"
QUEUE_AUDIO = "reelforge:audio"
QUEUE_DNA = "reelforge:dna"
QUEUE_BLUEPRINT = "reelforge:blueprint"
QUEUE_ASSEMBLE = "reelforge:assemble"
QUEUE_NOTIFY = "reelforge:notify"

# Job status pub/sub channel
CHANNEL_JOB_STATUS = "reelforge:job_status"


class RedisQueue:
    """Redis-based message queue for worker communication."""

    def __init__(self):
        settings = get_settings()
        self._redis = redis.from_url(
            settings.redis.url,
            decode_responses=True,
            socket_timeout=10,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )

    def push(self, queue_name: str, message: dict) -> None:
        """Push a message to a queue."""
        try:
            self._redis.rpush(queue_name, json.dumps(message))
            logger.info(f"Pushed message to {queue_name}: job_id={message.get('job_id', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to push to {queue_name}: {e}")
            raise

    def pop(self, queue_name: str, timeout: int = 0) -> Optional[dict]:
        """Pop a message from a queue. Blocks if timeout > 0."""
        try:
            if timeout > 0:
                result = self._redis.blpop(queue_name, timeout=timeout)
                if result:
                    _, data = result
                    return json.loads(data)
            else:
                data = self._redis.lpop(queue_name)
                if data:
                    return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to pop from {queue_name}: {e}")
            raise

    def queue_length(self, queue_name: str) -> int:
        """Get the number of messages in a queue."""
        return self._redis.llen(queue_name)

    def publish_status(self, job_id: str, status: str, progress: int = 0, **kwargs) -> None:
        """Publish a job status update to the pub/sub channel."""
        message = {
            "job_id": job_id,
            "status": status,
            "progress": progress,
            **kwargs,
        }
        self._redis.publish(CHANNEL_JOB_STATUS, json.dumps(message))

    def set_cache(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set a cache value with TTL."""
        self._redis.setex(key, ttl, json.dumps(value))

    def get_cache(self, key: str) -> Optional[Any]:
        """Get a cached value."""
        data = self._redis.get(key)
        if data:
            return json.loads(data)
        return None

    def delete_cache(self, key: str) -> None:
        """Delete a cached value."""
        self._redis.delete(key)

    def health_check(self) -> bool:
        """Check Redis connectivity."""
        try:
            return self._redis.ping()
        except Exception:
            return False


# Singleton instance
_queue_client: Optional[RedisQueue] = None


def get_queue() -> RedisQueue:
    """Get or create the singleton queue client."""
    global _queue_client
    if _queue_client is None:
        _queue_client = RedisQueue()
    return _queue_client
