"""ReelForge API — Middleware: Redis-backed rate limiting + RFC 7807 error handling."""

import logging
import time
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from shared.config import get_settings

logger = logging.getLogger(__name__)


# ── Redis-backed Rate Limiter ──

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket rate limiting backed by Redis for multi-worker correctness.
    Falls back to in-memory if Redis is unavailable (dev mode)."""

    def __init__(self, app: FastAPI, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        self._redis = None
        self._fallback: dict[str, list[float]] = {}  # in-memory fallback

    async def _get_redis(self):
        """Lazy-init Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                settings = get_settings()
                self._redis = aioredis.from_url(
                    settings.redis.url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                )
                await self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis rate-limit connect failed, using in-memory fallback: {e}")
                self._redis = False  # sentinel: don't retry
        return self._redis if self._redis is not False else None

    async def _is_rate_limited_redis(self, key: str, redis_conn) -> bool:
        """Sliding-window rate limit via Redis sorted set."""
        now = time.time()
        window_start = now - 60

        pipe = redis_conn.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, 120)
        results = await pipe.execute()

        count = results[2]
        return count > self.rpm

    def _is_rate_limited_memory(self, key: str) -> bool:
        """Fallback in-memory sliding window."""
        now = time.time()
        window_start = now - 60

        if key not in self._fallback:
            self._fallback[key] = []

        self._fallback[key] = [t for t in self._fallback[key] if t > window_start]
        self._fallback[key].append(now)

        return len(self._fallback[key]) > self.rpm

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and webhooks
        path = request.url.path
        if path in ("/health", "/api/v1/webhooks/stripe"):
            return await call_next(request)

        # Determine client key
        forwarded = request.headers.get("x-forwarded-for")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        rate_key = f"rl:{client_ip}:{path}"

        # Check rate limit
        redis_conn = await self._get_redis()
        if redis_conn:
            limited = await self._is_rate_limited_redis(rate_key, redis_conn)
        else:
            limited = self._is_rate_limited_memory(rate_key)

        if limited:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "type": "about:blank",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": f"Rate limit exceeded. Max {self.rpm} requests/minute.",
                },
            )

        return await call_next(request)


# ── Exception Handlers (RFC 7807) ──

async def http_exception_handler(request: Request, exc):
    """Return RFC 7807 Problem JSON for HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": exc.detail if isinstance(exc.detail, str) else "Error",
            "status": exc.status_code,
            "detail": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — never leak stack traces."""
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred. Please try again later.",
        },
    )


async def validation_exception_handler(request: Request, exc):
    """Return RFC 7807 for Pydantic validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": str(exc.errors()) if hasattr(exc, "errors") else str(exc),
            "errors": exc.errors() if hasattr(exc, "errors") else [],
        },
    )
