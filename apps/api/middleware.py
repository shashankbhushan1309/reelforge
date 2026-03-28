"""ReelForge API — Middleware and Exception Handlers."""

import time
import logging
from typing import Callable, Awaitable
from collections import defaultdict

from fastapi import Request, Response, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# Very simple in-memory rate limiter for demonstration/MVP
# In production, this would use Redis
_rate_limits = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware (Spec section 8).
    60 req/min unauthenticated.
    300 req/min authenticated (if bearer token is present).
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Determine client identifier (IP or token)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Authenticated
            limit = 300
            client_id = f"auth_{auth_header.split(' ')[1][:10]}"
        else:
            # Unauthenticated
            limit = 60
            client_id = f"ip_{request.client.host if request.client else 'unknown'}"

        now = time.time()
        window_start = now - 60

        # Clean old requests
        _rate_limits[client_id] = [t for t in _rate_limits[client_id] if t > window_start]

        if len(_rate_limits[client_id]) >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "type": "about:blank",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": "Rate limit exceeded. Try again later."
                },
                headers={"Retry-After": "60"}
            )

        _rate_limits[client_id].append(now)
        return await call_next(request)


def setup_exception_handlers(app: FastAPI):
    """Configure RFC 7807 Problem JSON for all errors."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": "about:blank",
                "title": getattr(exc, "title", "HTTP Error"),
                "status": exc.status_code,
                "detail": exc.detail,
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "type": "about:blank",
                "title": "Validation Error",
                "status": 422,
                "detail": "The request contains invalid parameters.",
                "errors": exc.errors()
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "type": "about:blank",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred."
            }
        )
