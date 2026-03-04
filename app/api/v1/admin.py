"""Administrative endpoints.

Provides tenant management operations: list tenants, reload
configurations, and view webhook audit logs.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.api.dependencies import get_webhook_store
from app.core.exceptions import (
    InvalidTenantConfigError,
    TenantNotFoundError,
)
from app.tenant.loader import (
    clear_cache,
    list_tenants,
    load_tenant,
    reload_tenant,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/tenants",
    summary="List all configured tenants",
    response_description="List of tenant IDs",
)
async def get_tenants() -> dict:
    """Return a list of all tenant IDs found on disk."""
    tenants = list_tenants()
    return {
        "count": len(tenants),
        "tenants": tenants,
    }


@router.get(
    "/tenants/{tenant_id}",
    summary="Get tenant configuration",
    response_description="Tenant settings",
)
async def get_tenant_config(tenant_id: str) -> dict:
    """Return the current configuration for a specific tenant.

    Args:
        tenant_id: Tenant identifier.

    Raises:
        HTTPException 404: If the tenant is not found.
    """
    try:
        settings = load_tenant(tenant_id)
        return {
            "tenant_id": tenant_id,
            "agent_name": settings.agent.name,
            "language": settings.agent.language,
            "cache_threshold": settings.cache.semantic_threshold,
            "cache_ttl_hours": settings.cache.ttl_hours,
            "business_hours": {
                "timezone": settings.business_hours.timezone,
                "monday_friday": settings.business_hours.schedule.monday_friday,
                "saturday": settings.business_hours.schedule.saturday,
                "sunday": settings.business_hours.schedule.sunday,
            },
            "escalation_keywords": settings.escalation.trigger_keywords,
            "webhook_endpoint": settings.webhooks.endpoint,
        }
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/tenants/{tenant_id}/reload",
    summary="Reload tenant configuration",
    response_description="Reload result",
)
async def reload_tenant_config(tenant_id: str) -> dict:
    """Force-reload a tenant's configuration from disk.

    Use this after editing a tenant's settings.yaml without
    restarting the application.

    Args:
        tenant_id: Tenant identifier.

    Raises:
        HTTPException 404: If the tenant is not found.
        HTTPException 422: If the configuration is invalid.
    """
    try:
        settings = reload_tenant(tenant_id)
        logger.info("Tenant reloaded: %s", tenant_id)
        return {
            "status": "reloaded",
            "tenant_id": tenant_id,
            "agent_name": settings.agent.name,
        }
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTenantConfigError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/tenants/reload-all",
    summary="Clear tenant cache and force reload",
    response_description="Cache clear result",
)
async def reload_all_tenants() -> dict:
    """Clear the tenant configuration cache.

    All tenants will be re-loaded from disk on next access.
    """
    clear_cache()
    tenants = list_tenants()
    logger.info("All tenant configs cleared, %d tenants on disk", len(tenants))
    return {
        "status": "cache_cleared",
        "tenants_available": len(tenants),
    }


@router.get(
    "/webhooks/received",
    summary="View received webhooks",
    response_description="List of received webhook payloads",
)
async def get_received_webhooks(
    tenant_id: str | None = None,
    limit: int = 50,
) -> dict:
    """Retrieve persisted received webhook events.

    Args:
        tenant_id: Filter by tenant (optional).
        limit: Maximum results to return.
    """
    store = get_webhook_store()
    received = store.get_received(tenant_id=tenant_id, limit=limit)
    return {
        "count": len(received),
        "webhooks": [
            {
                "event": w.event.value,
                "tenant_id": w.tenant_id,
                "timestamp": w.timestamp.isoformat(),
                "data": w.data,
            }
            for w in received
        ],
    }


@router.get(
    "/webhooks/deliveries",
    summary="View outbound webhook deliveries",
    response_description="List of webhook delivery records",
)
async def get_webhook_deliveries(
    tenant_id: str | None = None,
    limit: int = 50,
) -> dict:
    """Retrieve outbound webhook delivery records.

    Args:
        tenant_id: Filter by tenant (optional).
        limit: Maximum results to return.
    """
    store = get_webhook_store()
    deliveries = store.get_deliveries(tenant_id=tenant_id, limit=limit)
    return {
        "count": len(deliveries),
        "deliveries": [
            {
                "event": d.payload.event.value,
                "tenant_id": d.payload.tenant_id,
                "endpoint": d.endpoint,
                "status": d.status.value,
                "attempts": d.attempts,
                "last_attempt": (
                    d.last_attempt_at.isoformat()
                    if d.last_attempt_at else None
                ),
                "response_code": d.response_status_code,
            }
            for d in deliveries
        ],
    }
