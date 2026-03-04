"""Unit tests for agent core logic — orchestrator, cache, and conversation."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from app.core.agent import AgentOrchestrator
from app.core.cache import SemanticCacheService
from app.core.conversation import ConversationManager
from app.models.message import Message, MessageRole
from app.models.response import AgentResponse, ResponseSource
from app.tenant.models import (
    AgentConfig,
    BusinessHoursConfig,
    BusinessHoursSchedule,
    CacheConfig,
    EscalationConfig,
    TenantSettings,
    WebhooksConfig,
)


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture()
def mock_ai() -> AsyncMock:
    """Mock AI provider."""
    ai = AsyncMock()
    ai.generate_response = AsyncMock(
        return_value=AgentResponse(
            content="Olá! Como posso ajudar?",
            source=ResponseSource.AI,
            latency_ms=150.0,
        )
    )
    return ai


@pytest.fixture()
def mock_cache_provider() -> AsyncMock:
    """Mock cache provider."""
    cache = AsyncMock()
    cache.get_semantic = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


@pytest.fixture()
def mock_vector_store() -> AsyncMock:
    """Mock vector store."""
    store = AsyncMock()
    store.store_message = AsyncMock()
    store.get_history = AsyncMock(return_value=[])
    return store


@pytest.fixture()
def mock_whatsapp() -> AsyncMock:
    """Mock WhatsApp provider."""
    return AsyncMock()


@pytest.fixture()
def mock_webhooks() -> AsyncMock:
    """Mock webhook dispatcher."""
    webhooks = AsyncMock()
    webhooks.dispatch = AsyncMock(return_value=True)
    return webhooks


@pytest.fixture()
def cache_service(mock_cache_provider: AsyncMock) -> SemanticCacheService:
    """Cache service with mocked provider."""
    return SemanticCacheService(cache=mock_cache_provider)


@pytest.fixture()
def conversation(mock_vector_store: AsyncMock) -> ConversationManager:
    """Conversation manager with mocked store."""
    return ConversationManager(store=mock_vector_store)


@pytest.fixture()
def agent(
    mock_ai: AsyncMock,
    cache_service: SemanticCacheService,
    conversation: ConversationManager,
    mock_whatsapp: AsyncMock,
    mock_webhooks: AsyncMock,
) -> AgentOrchestrator:
    """Complete agent orchestrator with all mocked dependencies."""
    return AgentOrchestrator(
        ai_provider=mock_ai,
        cache_service=cache_service,
        conversation=conversation,
        whatsapp=mock_whatsapp,
        webhooks=mock_webhooks,
    )


def _make_settings(
    hours: str | None = "00:00-23:59",
    escalation_keywords: list[str] | None = None,
    webhook_endpoint: str | None = "https://example.com/webhook",
) -> TenantSettings:
    """Create a TenantSettings for testing."""
    return TenantSettings(
        agent=AgentConfig(
            name="Test Bot",
            system_prompt="You are a test bot.",
        ),
        business_hours=BusinessHoursConfig(
            timezone="UTC",
            schedule=BusinessHoursSchedule(
                monday_friday=hours,
                saturday=hours,
                sunday=hours,
            ),
            out_of_hours_message="Estamos fechados.",
        ),
        escalation=EscalationConfig(
            trigger_keywords=escalation_keywords or [],
            action="webhook",
            webhook_url="https://example.com/escalation",
            message="Conectando com humano...",
        ),
        cache=CacheConfig(
            semantic_threshold=0.92,
            ttl_hours=24,
        ),
        webhooks=WebhooksConfig(
            endpoint=webhook_endpoint,
            secret="test-secret",
        ),
    )


# ===================================================================
# Cache Service Tests
# ===================================================================

class TestSemanticCacheService:
    """Tests for SemanticCacheService."""

    @pytest.mark.asyncio
    async def test_try_cache_when_hit_should_return_cached_response(
        self, mock_cache_provider: AsyncMock
    ) -> None:
        mock_cache_provider.get_semantic.return_value = "Resposta do cache"
        service = SemanticCacheService(cache=mock_cache_provider)

        result = await service.try_cache("pergunta", 0.9, "tenant1")

        assert result is not None
        assert result.content == "Resposta do cache"
        assert result.source == ResponseSource.CACHE
        assert result.cached is True

    @pytest.mark.asyncio
    async def test_try_cache_when_miss_should_return_none(
        self, mock_cache_provider: AsyncMock
    ) -> None:
        mock_cache_provider.get_semantic.return_value = None
        service = SemanticCacheService(cache=mock_cache_provider)

        result = await service.try_cache("pergunta nova", 0.9, "tenant1")

        assert result is None

    @pytest.mark.asyncio
    async def test_store_should_call_provider_with_ttl_in_seconds(
        self, mock_cache_provider: AsyncMock
    ) -> None:
        service = SemanticCacheService(cache=mock_cache_provider)

        await service.store("query", "response", ttl_hours=12, tenant_id="t1")

        mock_cache_provider.set.assert_called_once_with(
            query="query",
            response="response",
            ttl=43200,  # 12 * 3600
            tenant_id="t1",
        )


# ===================================================================
# Conversation Manager Tests
# ===================================================================

class TestConversationManager:
    """Tests for ConversationManager."""

    @pytest.mark.asyncio
    async def test_add_message_should_store_in_vector_store(
        self, conversation: ConversationManager, mock_vector_store: AsyncMock
    ) -> None:
        msg = Message(role=MessageRole.USER, content="Oi")

        await conversation.add_message("t1", "s1", msg)

        mock_vector_store.store_message.assert_called_once_with(
            tenant_id="t1", session_id="s1", message=msg,
        )

    @pytest.mark.asyncio
    async def test_get_context_should_return_history(
        self, conversation: ConversationManager, mock_vector_store: AsyncMock
    ) -> None:
        expected = [
            Message(role=MessageRole.USER, content="Oi"),
            Message(role=MessageRole.ASSISTANT, content="Olá!"),
        ]
        mock_vector_store.get_history.return_value = expected

        result = await conversation.get_context("t1", "s1")

        assert result == expected
        mock_vector_store.get_history.assert_called_once()


# ===================================================================
# Agent Orchestrator Tests
# ===================================================================

class TestAgentOrchestrator:
    """Tests for AgentOrchestrator."""

    @pytest.mark.asyncio
    async def test_process_when_cache_hit_should_not_call_ai(
        self,
        agent: AgentOrchestrator,
        mock_ai: AsyncMock,
        mock_cache_provider: AsyncMock,
    ) -> None:
        mock_cache_provider.get_semantic.return_value = "Cached answer"
        settings = _make_settings()

        response = await agent.process_message(
            "t1", "s1", "5511999", "pergunta?", settings
        )

        assert response.content == "Cached answer"
        assert response.cached is True
        mock_ai.generate_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_when_cache_miss_should_call_ai_and_cache(
        self,
        agent: AgentOrchestrator,
        mock_ai: AsyncMock,
        mock_cache_provider: AsyncMock,
    ) -> None:
        mock_cache_provider.get_semantic.return_value = None
        settings = _make_settings()

        response = await agent.process_message(
            "t1", "s1", "5511999", "pergunta nova?", settings
        )

        assert response.source == ResponseSource.AI
        mock_ai.generate_response.assert_called_once()
        mock_cache_provider.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_should_store_history(
        self,
        agent: AgentOrchestrator,
        mock_vector_store: AsyncMock,
    ) -> None:
        settings = _make_settings()

        await agent.process_message(
            "t1", "s1", "5511999", "Oi", settings
        )

        # Should store user message + assistant message = 2 calls
        assert mock_vector_store.store_message.call_count == 2

    @pytest.mark.asyncio
    async def test_process_when_outside_hours_should_return_system_message(
        self, agent: AgentOrchestrator, mock_ai: AsyncMock
    ) -> None:
        # Schedule that is definitely closed now
        settings = _make_settings(hours="03:00-03:01")

        response = await agent.process_message(
            "t1", "s1", "5511999", "Oi", settings
        )

        assert response.source == ResponseSource.SYSTEM
        assert "fechados" in response.content.lower() or "fechado" in response.content.lower()
        mock_ai.generate_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_when_escalation_keyword_should_trigger_webhook(
        self,
        agent: AgentOrchestrator,
        mock_ai: AsyncMock,
        mock_webhooks: AsyncMock,
    ) -> None:
        settings = _make_settings(
            escalation_keywords=["falar com humano", "gerente"]
        )

        response = await agent.process_message(
            "t1", "s1", "5511999", "quero falar com humano", settings
        )

        assert response.source == ResponseSource.SYSTEM
        assert "Conectando" in response.content
        mock_ai.generate_response.assert_not_called()
        # Should dispatch escalation webhook
        mock_webhooks.dispatch.assert_called()
        dispatch_calls = mock_webhooks.dispatch.call_args_list
        events = [
            call.kwargs.get("event", call.args[0] if call.args else None)
            for call in dispatch_calls
        ]
        assert "escalation_triggered" in events

    @pytest.mark.asyncio
    async def test_process_should_send_whatsapp_response(
        self,
        agent: AgentOrchestrator,
        mock_whatsapp: AsyncMock,
    ) -> None:
        settings = _make_settings()

        await agent.process_message(
            "t1", "s1", "5511999", "Oi", settings
        )

        mock_whatsapp.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_should_dispatch_message_received_webhook(
        self,
        agent: AgentOrchestrator,
        mock_webhooks: AsyncMock,
    ) -> None:
        settings = _make_settings()

        await agent.process_message(
            "t1", "s1", "5511999", "Oi", settings
        )

        mock_webhooks.dispatch.assert_called()
