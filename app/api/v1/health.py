"""Health check endpoint.

Exposes the application's health status and the status of each
external dependency (Redis, Qdrant, WAHA).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import (
    get_cache_provider,
    get_vector_store,
    get_whatsapp_provider,
)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Application health check",
    response_description="Health status of the application and its dependencies",
)
async def health_check() -> dict:
    """Return the health status of all dependencies.

    Checks connectivity to Redis, Qdrant, and WAHA.
    Returns HTTP 200 even if a dependency is down — the response
    body indicates individual service status.
    """
    redis_ok = await _check_redis()
    qdrant_ok = await _check_qdrant()
    waha_ok = await _check_waha()

    all_healthy = redis_ok and qdrant_ok and waha_ok

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": {
            "redis": "up" if redis_ok else "down",
            "qdrant": "up" if qdrant_ok else "down",
            "waha": "up" if waha_ok else "down",
        },
    }


async def _check_redis() -> bool:
    """Check Redis connectivity."""
    try:
        provider = get_cache_provider()
        return await provider.health_check()  # type: ignore[attr-defined]
    except Exception:
        return False


async def _check_qdrant() -> bool:
    """Check Qdrant connectivity."""
    try:
        store = get_vector_store()
        return await store.health_check()  # type: ignore[attr-defined]
    except Exception:
        return False


async def _check_waha() -> bool:
    """Check WAHA connectivity."""
    try:
        provider = get_whatsapp_provider()
        return await provider.health_check()  # type: ignore[attr-defined]
    except Exception:
        return False
