"""ReelForge AI — FastAPI Application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_settings

from apps.api.middleware import RateLimitMiddleware, setup_exception_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    logger.info("🎬 ReelForge AI API starting up...")
    yield
    logger.info("🎬 ReelForge AI API shutting down...")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ReelForge AI",
        description="Zero-edit AI video director for short-form content",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware)

    # Setup RFC 7807 Exception Handlers
    setup_exception_handlers(app)

    # Import and register routers
    from apps.api.routers import upload, jobs, reels, vault, trends, dna_templates, auth, webhooks

    app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
    app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])
    app.include_router(reels.router, prefix="/api/v1", tags=["Reels"])
    app.include_router(vault.router, prefix="/api/v1", tags=["Vault"])
    app.include_router(trends.router, prefix="/api/v1", tags=["Trends"])
    app.include_router(dna_templates.router, prefix="/api/v1", tags=["DNA Templates"])
    app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "service": "reelforge-api", "version": "0.1.0"}

    return app


app = create_app()
