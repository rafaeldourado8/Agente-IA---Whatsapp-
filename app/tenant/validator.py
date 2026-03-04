"""Tenant configuration validator.

Validates a tenant's settings.yaml against the Pydantic schema
at load time, ensuring fast failure with clear error messages.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.core.exceptions import InvalidTenantConfigError, TenantNotFoundError
from app.tenant.models import TenantSettings
from app.tenant.prompt_builder import build_system_prompt

logger = logging.getLogger(__name__)


def validate_tenant_config(tenant_dir: Path) -> TenantSettings:
    """Parse and validate a tenant's settings.yaml.

    If the system_prompt field is empty, it is auto-generated
    from the company configuration data.

    Args:
        tenant_dir: Path to the tenant's directory (must contain settings.yaml).

    Returns:
        Validated TenantSettings instance.

    Raises:
        TenantNotFoundError: If the tenant directory or settings.yaml doesn't exist.
        InvalidTenantConfigError: If the YAML is malformed or fails schema validation.
    """
    settings_path = tenant_dir / "settings.yaml"

    if not tenant_dir.is_dir():
        raise TenantNotFoundError(
            f"Tenant directory not found: {tenant_dir}"
        )

    if not settings_path.is_file():
        raise TenantNotFoundError(
            f"Tenant settings file not found: {settings_path}"
        )

    raw_content = _read_yaml(settings_path)
    settings = _parse_settings(raw_content, settings_path)

    # Auto-generate system prompt from company data if not provided
    if not settings.agent.system_prompt:
        settings.agent.system_prompt = build_system_prompt(
            company=settings.company,
            agent=settings.agent,
        )
        logger.info(
            "System prompt auto-generated for tenant: %s",
            settings_path,
        )

    return settings


def _read_yaml(path: Path) -> dict:
    """Read and parse a YAML file into a dictionary.

    Args:
        path: Path to the YAML file.

    Returns:
        Dictionary with the YAML content.

    Raises:
        InvalidTenantConfigError: If the YAML syntax is invalid.
    """
    try:
        with open(path, encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise InvalidTenantConfigError(
            f"Invalid YAML syntax in {path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise InvalidTenantConfigError(
            f"Expected a YAML mapping in {path}, got {type(data).__name__}"
        )

    return data


def _parse_settings(raw: dict, source_path: Path) -> TenantSettings:
    """Validate raw YAML data against the TenantSettings schema.

    Args:
        raw: Dictionary parsed from settings.yaml.
        source_path: Path to the file (for error messages).

    Returns:
        Validated TenantSettings instance.

    Raises:
        InvalidTenantConfigError: If schema validation fails.
    """
    try:
        settings = TenantSettings(**raw)
    except ValidationError as exc:
        error_count = exc.error_count()
        error_details = exc.errors()
        fields = [
            ".".join(str(loc) for loc in err["loc"])
            for err in error_details
        ]
        raise InvalidTenantConfigError(
            f"{error_count} validation error(s) in {source_path}: "
            f"fields={fields}"
        ) from exc

    logger.info("Tenant config validated: %s", source_path)
    return settings
