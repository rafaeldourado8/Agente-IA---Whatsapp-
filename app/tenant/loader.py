"""Tenant configuration loader.

Provides tenant lookup by ID. The tenant ID is the directory name
under the configured TENANT_CONFIG_DIR. Loaded configs are cached
in memory for fast repeated access.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import get_settings
from app.core.exceptions import TenantNotFoundError
from app.tenant.models import TenantSettings
from app.tenant.validator import validate_tenant_config

logger = logging.getLogger(__name__)

# In-memory cache: tenant_id → validated settings
_tenant_cache: dict[str, TenantSettings] = {}


def load_tenant(tenant_id: str) -> TenantSettings:
    """Load and return the validated configuration for a tenant.

    Results are cached in memory. Use ``reload_tenant`` to force
    a fresh read from disk.

    Args:
        tenant_id: Identifier matching the directory name under tenants/.

    Returns:
        Validated TenantSettings instance.

    Raises:
        TenantNotFoundError: If no directory exists for this tenant_id.
        InvalidTenantConfigError: If the settings.yaml is invalid.
    """
    if tenant_id in _tenant_cache:
        logger.debug("Tenant '%s' loaded from cache", tenant_id)
        return _tenant_cache[tenant_id]

    tenant_dir = _resolve_tenant_dir(tenant_id)
    settings = validate_tenant_config(tenant_dir)
    _tenant_cache[tenant_id] = settings

    logger.info("Tenant '%s' loaded and cached", tenant_id)
    return settings


def reload_tenant(tenant_id: str) -> TenantSettings:
    """Force-reload a tenant's configuration from disk.

    Useful for admin endpoints that update configs at runtime.

    Args:
        tenant_id: Identifier of the tenant to reload.

    Returns:
        Freshly validated TenantSettings instance.
    """
    _tenant_cache.pop(tenant_id, None)
    return load_tenant(tenant_id)


def list_tenants() -> list[str]:
    """Return a list of all tenant IDs found on disk.

    A tenant is any subdirectory of TENANT_CONFIG_DIR that contains
    a ``settings.yaml`` file.

    Returns:
        Sorted list of tenant identifiers.
    """
    base_dir = Path(get_settings().TENANT_CONFIG_DIR)
    if not base_dir.is_dir():
        logger.warning("Tenant config dir does not exist: %s", base_dir)
        return []

    tenants = [
        entry.name
        for entry in base_dir.iterdir()
        if entry.is_dir() and (entry / "settings.yaml").is_file()
    ]
    return sorted(tenants)


def clear_cache() -> None:
    """Clear all cached tenant configurations."""
    _tenant_cache.clear()
    logger.info("Tenant cache cleared")


def _resolve_tenant_dir(tenant_id: str) -> Path:
    """Resolve the tenant directory path and verify it exists.

    Args:
        tenant_id: Tenant identifier.

    Returns:
        Path to the tenant's directory.

    Raises:
        TenantNotFoundError: If the directory doesn't exist.
    """
    base_dir = Path(get_settings().TENANT_CONFIG_DIR)
    tenant_dir = base_dir / tenant_id

    if not tenant_dir.is_dir():
        raise TenantNotFoundError(
            f"Tenant '{tenant_id}' not found in {base_dir}"
        )

    return tenant_dir
