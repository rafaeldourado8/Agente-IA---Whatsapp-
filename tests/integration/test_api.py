"""Integration tests for the API layer.

Tests the full HTTP request/response cycle using FastAPI's
TestClient with mocked service dependencies.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models.response import AgentResponse, ResponseSource


@pytest.fixture()
def mock_services(monkeypatch: pytest.MonkeyPatch):
    """Mock all service singletons in the dependencies module."""
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("REDIS_PASSWORD", "test")
    monkeypatch.setenv("WAHA_API_KEY", "test")
    monkeypatch.setenv("TENANT_CONFIG_DIR", "./tenants")

    from app.config import get_settings
    get_settings.cache_clear()

    import app.api.dependencies as deps

    # Mock service singletons
    mock_cache = AsyncMock()
    mock_cache.health_check = AsyncMock(return_value=True)
    mock_qdrant = AsyncMock()
    mock_qdrant.health_check = AsyncMock(return_value=True)
    mock_waha = AsyncMock()
    mock_waha.health_check = AsyncMock(return_value=True)
    mock_webhook_store = MagicMock()
    mock_webhook_store.persist_received = MagicMock()
    mock_webhook_store.get_received = MagicMock(return_value=[])
    mock_webhook_store.get_deliveries = MagicMock(return_value=[])

    mock_agent = AsyncMock()
    mock_agent.process_message = AsyncMock(
        return_value=AgentResponse(
            content="Olá! Como posso ajudar?",
            source=ResponseSource.AI,
            latency_ms=100.0,
        )
    )

    monkeypatch.setattr(deps, "_redis_cache", mock_cache)
    monkeypatch.setattr(deps, "_qdrant_store", mock_qdrant)
    monkeypatch.setattr(deps, "_waha_provider", mock_waha)
    monkeypatch.setattr(deps, "_webhook_store", mock_webhook_store)
    monkeypatch.setattr(deps, "_agent", mock_agent)

    return {
        "cache": mock_cache,
        "qdrant": mock_qdrant,
        "waha": mock_waha,
        "webhook_store": mock_webhook_store,
        "agent": mock_agent,
    }


@pytest.fixture()
def client(mock_services) -> TestClient:
    """Create a FastAPI test client with mocked services."""
    from app.main import create_app

    app = create_app()
    # Override lifespan to skip real service init
    app.router.lifespan_context = _noop_lifespan
    return TestClient(app)


from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi import FastAPI


@asynccontextmanager
async def _noop_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """No-op lifespan for testing — services are already mocked."""
    yield


# ===================================================================
# Health Check Tests
# ===================================================================

class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_when_all_up_should_return_healthy(
        self, client: TestClient
    ) -> None:
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["services"]["redis"] == "up"
        assert data["services"]["qdrant"] == "up"
        assert data["services"]["waha"] == "up"

    def test_health_when_redis_down_should_return_degraded(
        self, client: TestClient, mock_services: dict
    ) -> None:
        mock_services["cache"].health_check.return_value = False

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["redis"] == "down"


# ===================================================================
# Webhook Endpoint Tests
# ===================================================================

class TestWebhookEndpoint:
    """Tests for POST /api/v1/webhook/message."""

    def test_receive_message_when_valid_should_return_response(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/v1/webhook/message",
            json={
                "instance": "default",
                "phone": "5511999999999",
                "message": "Olá!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["response"] == "Olá! Como posso ajudar?"
        assert data["source"] == "ai"

    def test_receive_message_when_tenant_missing_should_return_404(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/v1/webhook/message",
            json={
                "instance": "nonexistent_tenant",
                "phone": "5511999999999",
                "message": "Olá!",
            },
        )

        assert response.status_code == 404

    def test_receive_message_when_body_invalid_should_return_422(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/v1/webhook/message",
            json={"bad": "data"},
        )

        assert response.status_code == 422


# ===================================================================
# Admin Endpoint Tests
# ===================================================================

class TestAdminEndpoints:
    """Tests for /api/v1/admin/* endpoints."""

    def test_list_tenants_should_return_list(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/admin/tenants")

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "tenants" in data

    def test_get_tenant_when_exists_should_return_config(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/admin/tenants/default")

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "default"
        assert "agent_name" in data

    def test_get_tenant_when_missing_should_return_404(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/admin/tenants/nonexistent")

        assert response.status_code == 404

    def test_reload_all_should_clear_cache(
        self, client: TestClient
    ) -> None:
        response = client.post("/api/v1/admin/tenants/reload-all")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cache_cleared"

    def test_get_received_webhooks_should_return_list(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/admin/webhooks/received")

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "webhooks" in data

    def test_get_deliveries_should_return_list(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/v1/admin/webhooks/deliveries")

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "deliveries" in data


# ===================================================================
# WAHA Native Webhook Tests
# ===================================================================

class TestWahaWebhookEndpoint:
    """Tests for POST /api/v1/webhook/waha."""

    def test_waha_message_when_valid_should_process(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/v1/webhook/waha",
            json={
                "event": "message",
                "session": "default",
                "payload": {
                    "from": "5511999999999@c.us",
                    "body": "Olá!",
                    "fromMe": False,
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["response"] == "Olá! Como posso ajudar?"

    def test_waha_message_when_from_me_should_ignore(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/v1/webhook/waha",
            json={
                "event": "message",
                "session": "default",
                "payload": {
                    "from": "5511999999999@c.us",
                    "body": "My own message",
                    "fromMe": True,
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    def test_waha_event_when_not_message_should_ignore(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/v1/webhook/waha",
            json={
                "event": "session.status",
                "session": "default",
                "payload": {"status": "WORKING"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    def test_waha_message_when_empty_body_should_ignore(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/v1/webhook/waha",
            json={
                "event": "message",
                "session": "default",
                "payload": {
                    "from": "5511999999999@c.us",
                    "body": "",
                    "fromMe": False,
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
