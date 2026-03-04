"""FastAPI application entrypoint.

Creates the ASGI application, configures middleware,
mounts versioned API routers, and sets up structured logging.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.dependencies import init_services, shutdown_services
from app.api.v1.admin import router as admin_router
from app.api.v1.health import router as health_router
from app.api.v1.webhooks import router as webhooks_router
from app.config import get_settings
from app.logging_config import configure_logging


def _configure_logging() -> None:
    """Configure structured JSON logging based on the LOG_LEVEL env var."""
    settings = get_settings()
    use_json = settings.LOG_LEVEL.upper() != "DEBUG"
    configure_logging(level=settings.LOG_LEVEL, json_format=use_json)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks.

    Startup: configure logging, initialize all services.
    Shutdown: gracefully disconnect external services.
    """
    _configure_logging()
    logger = logging.getLogger("app.main")
    logger.info("Starting WhatsApp B2B AI Agent")
    logger.info("Tenant config dir: %s", get_settings().TENANT_CONFIG_DIR)

    await init_services()
    logger.info("All services initialized")

    yield

    await shutdown_services()
    logger.info("Shutting down WhatsApp B2B AI Agent")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    application = FastAPI(
        title="WhatsApp B2B AI Agent",
        description="Multi-tenant WhatsApp AI agent for B2B customer support",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    application.include_router(health_router)
    application.include_router(webhooks_router, prefix="/api/v1")
    application.include_router(admin_router, prefix="/api/v1")

    return application


app = create_app()
