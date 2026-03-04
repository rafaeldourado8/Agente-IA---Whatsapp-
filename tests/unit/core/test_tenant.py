"""Unit tests for tenant configuration loading, validation, and caching."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from app.core.exceptions import InvalidTenantConfigError, TenantNotFoundError
from app.tenant.loader import clear_cache, list_tenants, load_tenant, reload_tenant
from app.tenant.models import TenantSettings
from app.tenant.validator import validate_tenant_config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_SETTINGS: dict = {
    "agent": {
        "name": "Bot de Teste",
        "personality": "Amigável",
        "language": "pt-BR",
        "system_prompt": "Você é um assistente de teste.",
    },
    "topics": {
        "allowed": ["suporte"],
        "blocked": ["política"],
    },
    "business_hours": {
        "timezone": "America/Sao_Paulo",
        "schedule": {
            "monday_friday": "08:00-18:00",
            "saturday": "09:00-13:00",
            "sunday": None,
        },
        "out_of_hours_message": "Fora do horário.",
    },
    "cache": {
        "semantic_threshold": 0.90,
        "ttl_hours": 12,
    },
}

MINIMAL_SETTINGS: dict = {
    "agent": {
        "name": "Bot Mínimo",
        "system_prompt": "Responda com educação.",
    },
}


@pytest.fixture()
def tenant_dir(tmp_path: Path) -> Path:
    """Create a temporary tenant directory with a valid settings.yaml."""
    tenant = tmp_path / "test_tenant"
    tenant.mkdir()
    settings_file = tenant / "settings.yaml"
    with open(settings_file, "w", encoding="utf-8") as f:
        yaml.dump(VALID_SETTINGS, f, allow_unicode=True)
    return tenant


@pytest.fixture()
def minimal_tenant_dir(tmp_path: Path) -> Path:
    """Create a tenant directory with only the required fields."""
    tenant = tmp_path / "minimal_tenant"
    tenant.mkdir()
    settings_file = tenant / "settings.yaml"
    with open(settings_file, "w", encoding="utf-8") as f:
        yaml.dump(MINIMAL_SETTINGS, f, allow_unicode=True)
    return tenant


@pytest.fixture()
def tenants_root(tmp_path: Path) -> Path:
    """Create a tenants root directory with two valid tenants."""
    root = tmp_path / "tenants"
    root.mkdir()

    for name, settings in [("alpha", VALID_SETTINGS), ("beta", MINIMAL_SETTINGS)]:
        tenant = root / name
        tenant.mkdir()
        with open(tenant / "settings.yaml", "w", encoding="utf-8") as f:
            yaml.dump(settings, f, allow_unicode=True)

    return root


@pytest.fixture(autouse=True)
def _clear_cache_between_tests():
    """Clear the tenant cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


# ---------------------------------------------------------------------------
# Validator Tests
# ---------------------------------------------------------------------------

class TestValidateTenantConfig:
    """Tests for validate_tenant_config."""

    def test_valid_config_when_all_fields_present_should_return_settings(
        self, tenant_dir: Path
    ) -> None:
        settings = validate_tenant_config(tenant_dir)

        assert isinstance(settings, TenantSettings)
        assert settings.agent.name == "Bot de Teste"
        assert settings.agent.language == "pt-BR"
        assert settings.cache.semantic_threshold == 0.90
        assert settings.cache.ttl_hours == 12

    def test_valid_config_when_minimal_fields_should_use_defaults(
        self, minimal_tenant_dir: Path
    ) -> None:
        settings = validate_tenant_config(minimal_tenant_dir)

        assert settings.agent.name == "Bot Mínimo"
        assert settings.agent.personality == "Profissional e simpático"
        assert settings.cache.semantic_threshold == 0.92
        assert settings.cache.ttl_hours == 24

    def test_invalid_config_when_missing_agent_should_raise_error(
        self, tmp_path: Path
    ) -> None:
        tenant = tmp_path / "bad_tenant"
        tenant.mkdir()
        with open(tenant / "settings.yaml", "w", encoding="utf-8") as f:
            yaml.dump({"topics": {"allowed": ["test"]}}, f)

        with pytest.raises(InvalidTenantConfigError):
            validate_tenant_config(tenant)

    def test_invalid_config_when_bad_yaml_should_raise_error(
        self, tmp_path: Path
    ) -> None:
        tenant = tmp_path / "malformed"
        tenant.mkdir()
        with open(tenant / "settings.yaml", "w", encoding="utf-8") as f:
            f.write("agent:\n  name: 'Test\n  bad_indent")

        with pytest.raises(InvalidTenantConfigError):
            validate_tenant_config(tenant)

    def test_invalid_config_when_threshold_out_of_range_should_raise_error(
        self, tmp_path: Path
    ) -> None:
        tenant = tmp_path / "bad_threshold"
        tenant.mkdir()
        bad_settings = {
            "agent": {
                "name": "Test",
                "system_prompt": "Hello",
            },
            "cache": {"semantic_threshold": 2.0},
        }
        with open(tenant / "settings.yaml", "w", encoding="utf-8") as f:
            yaml.dump(bad_settings, f)

        with pytest.raises(InvalidTenantConfigError):
            validate_tenant_config(tenant)

    def test_not_found_when_dir_missing_should_raise_error(
        self, tmp_path: Path
    ) -> None:
        with pytest.raises(TenantNotFoundError):
            validate_tenant_config(tmp_path / "nonexistent")

    def test_not_found_when_yaml_missing_should_raise_error(
        self, tmp_path: Path
    ) -> None:
        empty_dir = tmp_path / "empty_tenant"
        empty_dir.mkdir()

        with pytest.raises(TenantNotFoundError):
            validate_tenant_config(empty_dir)


# ---------------------------------------------------------------------------
# Loader Tests
# ---------------------------------------------------------------------------

class TestLoadTenant:
    """Tests for load_tenant, reload_tenant, and list_tenants."""

    def test_load_tenant_when_valid_should_return_settings(
        self, tenants_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TENANT_CONFIG_DIR", str(tenants_root))
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        monkeypatch.setenv("REDIS_PASSWORD", "test")
        monkeypatch.setenv("EVOLUTION_API_KEY", "test")

        # Force re-creation of settings with new env
        from app.config import get_settings
        get_settings.cache_clear()

        settings = load_tenant("alpha")
        assert settings.agent.name == "Bot de Teste"

    def test_load_tenant_when_not_found_should_raise_error(
        self, tenants_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TENANT_CONFIG_DIR", str(tenants_root))
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        monkeypatch.setenv("REDIS_PASSWORD", "test")
        monkeypatch.setenv("EVOLUTION_API_KEY", "test")

        from app.config import get_settings
        get_settings.cache_clear()

        with pytest.raises(TenantNotFoundError):
            load_tenant("does_not_exist")

    def test_load_tenant_when_called_twice_should_use_cache(
        self, tenants_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TENANT_CONFIG_DIR", str(tenants_root))
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        monkeypatch.setenv("REDIS_PASSWORD", "test")
        monkeypatch.setenv("EVOLUTION_API_KEY", "test")

        from app.config import get_settings
        get_settings.cache_clear()

        first = load_tenant("alpha")
        second = load_tenant("alpha")
        assert first is second

    def test_reload_tenant_when_called_should_return_fresh(
        self, tenants_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TENANT_CONFIG_DIR", str(tenants_root))
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        monkeypatch.setenv("REDIS_PASSWORD", "test")
        monkeypatch.setenv("EVOLUTION_API_KEY", "test")

        from app.config import get_settings
        get_settings.cache_clear()

        first = load_tenant("alpha")
        second = reload_tenant("alpha")
        assert first is not second
        assert first.agent.name == second.agent.name

    def test_list_tenants_when_tenants_exist_should_return_sorted_ids(
        self, tenants_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TENANT_CONFIG_DIR", str(tenants_root))
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        monkeypatch.setenv("REDIS_PASSWORD", "test")
        monkeypatch.setenv("EVOLUTION_API_KEY", "test")

        from app.config import get_settings
        get_settings.cache_clear()

        tenants = list_tenants()
        assert tenants == ["alpha", "beta"]
