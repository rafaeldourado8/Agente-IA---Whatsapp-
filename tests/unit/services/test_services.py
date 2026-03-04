"""Unit tests for infrastructure services with mocked external dependencies."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import numpy as np
import pytest

from app.core.exceptions import CacheOperationError, WhatsAppDeliveryError
from app.models.message import Message, MessageRole
from app.models.webhook import DeliveryStatus, WebhookEvent
from app.services.cache.redis_cache import RedisCacheProvider
from app.services.webhook.webhook_store import WebhookStore
from app.services.whatsapp.evolution_api import EvolutionAPIProvider


# ===================================================================
# Redis Cache Tests
# ===================================================================

class TestRedisCacheProvider:
    """Tests for RedisCacheProvider."""

    @pytest.fixture()
    def mock_redis(self) -> AsyncMock:
        """Create a mock async Redis client."""
        client = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock(return_value=True)
        client.sadd = AsyncMock(return_value=1)
        client.smembers = AsyncMock(return_value=set())
        client.delete = AsyncMock(return_value=1)
        client.scan_iter = MagicMock(return_value=AsyncIterMock([]))
        return client

    @pytest.fixture()
    def embedding_fn(self) -> AsyncMock:
        """Create a mock embedding function."""
        fn = AsyncMock()
        fn.return_value = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        return fn

    @pytest.fixture()
    def cache(
        self, mock_redis: AsyncMock, embedding_fn: AsyncMock
    ) -> RedisCacheProvider:
        """Create a RedisCacheProvider with mocked dependencies."""
        return RedisCacheProvider(client=mock_redis, embedding_fn=embedding_fn)

    @pytest.mark.asyncio
    async def test_set_when_valid_should_store_in_redis(
        self, cache: RedisCacheProvider, mock_redis: AsyncMock
    ) -> None:
        await cache.set("what are your hours?", "8am to 6pm", ttl=3600)

        mock_redis.set.assert_called_once()
        mock_redis.sadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_semantic_when_no_entries_should_return_none(
        self, cache: RedisCacheProvider
    ) -> None:
        result = await cache.get_semantic("hello", threshold=0.9)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_semantic_when_similar_entry_should_return_response(
        self,
        cache: RedisCacheProvider,
        mock_redis: AsyncMock,
        embedding_fn: AsyncMock,
    ) -> None:
        # Arrange: same embedding = perfect similarity
        embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        cached_entry = {
            "query": "business hours?",
            "response": "8am to 6pm",
            "embedding": embedding.tolist(),
        }
        mock_redis.smembers.return_value = {"cache:default:abc123"}
        mock_redis.get.return_value = json.dumps(cached_entry)

        result = await cache.get_semantic("what are your hours?", threshold=0.9)

        assert result == "8am to 6pm"

    @pytest.mark.asyncio
    async def test_get_semantic_when_low_similarity_should_return_none(
        self,
        cache: RedisCacheProvider,
        mock_redis: AsyncMock,
        embedding_fn: AsyncMock,
    ) -> None:
        # Arrange: orthogonal vectors = zero similarity
        query_embedding = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        cached_embedding = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        embedding_fn.return_value = query_embedding

        cached_entry = {
            "query": "unrelated question",
            "response": "unrelated answer",
            "embedding": cached_embedding.tolist(),
        }
        mock_redis.smembers.return_value = {"cache:default:xyz789"}
        mock_redis.get.return_value = json.dumps(cached_entry)

        result = await cache.get_semantic("my question", threshold=0.9)

        assert result is None

    @pytest.mark.asyncio
    async def test_health_check_when_redis_up_should_return_true(
        self, cache: RedisCacheProvider
    ) -> None:
        result = await cache.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_clear_tenant_when_keys_exist_should_delete_them(
        self, cache: RedisCacheProvider, mock_redis: AsyncMock
    ) -> None:
        mock_redis.scan_iter = MagicMock(
            return_value=AsyncIterMock(["cache:acme:a", "cache:acme:b"])
        )

        count = await cache.clear_tenant("acme")

        assert count == 2
        mock_redis.delete.assert_called_once()


# ===================================================================
# Evolution API Tests
# ===================================================================

class TestEvolutionAPIProvider:
    """Tests for EvolutionAPIProvider."""

    @pytest.fixture()
    def mock_client(self) -> AsyncMock:
        """Create a mock httpx async client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.is_success = True
        response.raise_for_status = MagicMock()
        client.post = AsyncMock(return_value=response)
        client.get = AsyncMock(return_value=response)
        return client

    @pytest.fixture()
    def provider(self, mock_client: AsyncMock) -> EvolutionAPIProvider:
        """Create provider with mocked client."""
        return EvolutionAPIProvider(
            base_url="http://test:8080",
            api_key="test-key",
            client=mock_client,
        )

    @pytest.mark.asyncio
    async def test_send_message_when_success_should_post_to_api(
        self,
        provider: EvolutionAPIProvider,
        mock_client: AsyncMock,
    ) -> None:
        await provider.send_message("5511999999999", "Olá!")

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "sendText" in call_args[0][0]
        assert call_args[1]["json"]["number"] == "5511999999999"

    @pytest.mark.asyncio
    async def test_send_message_when_api_error_should_raise_error(
        self,
        provider: EvolutionAPIProvider,
        mock_client: AsyncMock,
    ) -> None:
        request = httpx.Request("POST", "http://test/send")
        error_response = httpx.Response(500, request=request, text="Server Error")
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=request,
                response=error_response,
            )
        )

        with pytest.raises(WhatsAppDeliveryError):
            await provider.send_message("5511999999999", "Olá!")

    @pytest.mark.asyncio
    async def test_health_check_when_api_up_should_return_true(
        self, provider: EvolutionAPIProvider
    ) -> None:
        result = await provider.health_check()
        assert result is True


# ===================================================================
# Webhook Store Tests
# ===================================================================

class TestWebhookStore:
    """Tests for WebhookStore."""

    @pytest.fixture()
    def mock_client(self) -> AsyncMock:
        """Create a mock httpx client for webhooks."""
        client = AsyncMock(spec=httpx.AsyncClient)
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.is_success = True
        client.post = AsyncMock(return_value=response)
        return client

    @pytest.fixture()
    def store(self, mock_client: AsyncMock) -> WebhookStore:
        """Create a WebhookStore with mocked client."""
        return WebhookStore(client=mock_client, max_retries=2)

    @pytest.mark.asyncio
    async def test_dispatch_when_success_should_return_true(
        self, store: WebhookStore
    ) -> None:
        result = await store.dispatch(
            event="message_received",
            payload={"tenant_id": "acme", "content": "hello"},
            endpoint="https://example.com/webhook",
            secret="test-secret",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_dispatch_when_success_should_persist_delivery(
        self, store: WebhookStore
    ) -> None:
        await store.dispatch(
            event="message_received",
            payload={"tenant_id": "acme"},
            endpoint="https://example.com/webhook",
            secret="s",
        )

        deliveries = store.get_deliveries()
        assert len(deliveries) == 1
        assert deliveries[0].status == DeliveryStatus.DELIVERED

    @pytest.mark.asyncio
    async def test_dispatch_when_all_retries_fail_should_return_false(
        self,
        store: WebhookStore,
        mock_client: AsyncMock,
    ) -> None:
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        result = await store.dispatch(
            event="escalation_triggered",
            payload={"tenant_id": "acme"},
            endpoint="https://example.com/webhook",
            secret="s",
        )

        assert result is False
        assert mock_client.post.call_count == 2  # max_retries=2

    @pytest.mark.asyncio
    async def test_dispatch_when_failed_should_persist_as_failed(
        self,
        store: WebhookStore,
        mock_client: AsyncMock,
    ) -> None:
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        await store.dispatch(
            event="session_started",
            payload={"tenant_id": "acme"},
            endpoint="https://example.com/webhook",
            secret="s",
        )

        deliveries = store.get_deliveries()
        assert len(deliveries) == 1
        assert deliveries[0].status == DeliveryStatus.FAILED

    def test_persist_received_should_store_payload(
        self, store: WebhookStore
    ) -> None:
        from app.models.webhook import WebhookPayload

        payload = WebhookPayload(
            event=WebhookEvent.MESSAGE_RECEIVED,
            tenant_id="acme",
            data={"phone": "123"},
        )

        store.persist_received(payload)

        received = store.get_received()
        assert len(received) == 1
        assert received[0].tenant_id == "acme"

    def test_get_received_when_filtered_by_tenant_should_return_subset(
        self, store: WebhookStore
    ) -> None:
        from app.models.webhook import WebhookPayload

        store.persist_received(WebhookPayload(
            event=WebhookEvent.MESSAGE_RECEIVED,
            tenant_id="acme",
        ))
        store.persist_received(WebhookPayload(
            event=WebhookEvent.MESSAGE_RECEIVED,
            tenant_id="beta",
        ))

        acme_received = store.get_received(tenant_id="acme")
        assert len(acme_received) == 1
        assert acme_received[0].tenant_id == "acme"


# ===================================================================
# Helpers
# ===================================================================

class AsyncIterMock:
    """Helper to mock async iterators (e.g. redis.scan_iter)."""

    def __init__(self, items: list) -> None:
        self._items = items
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item
