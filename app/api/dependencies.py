"""FastAPI dependency injection.

Provides factory functions for all services, injected into
route handlers through FastAPI's Depends() mechanism.
All dependencies return abstractions (ABCs), never implementations.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import AsyncGenerator

from app.config import get_settings
from app.core.agent import AgentOrchestrator
from app.core.cache import SemanticCacheService
from app.core.conversation import ConversationManager
from app.core.interfaces import (
    AIProvider,
    CacheProvider,
    VectorStoreProvider,
    WebhookDispatcher,
    WhatsAppProvider,
)
from app.services.cache.redis_cache import RedisCacheProvider
from app.services.vector_store.qdrant_store import QdrantVectorStore
from app.services.webhook.webhook_store import WebhookStore
from app.services.whatsapp.waha_api import WAHAProvider

logger = logging.getLogger(__name__)

# Singletons — initialized once, reused across requests
_redis_cache: RedisCacheProvider | None = None
_qdrant_store: QdrantVectorStore | None = None
_waha_provider: WAHAProvider | None = None
_webhook_store: WebhookStore | None = None
_agent: AgentOrchestrator | None = None


async def init_services() -> None:
    """Initialize and connect all service singletons.

    Called during application startup (lifespan).
    """
    global _redis_cache, _qdrant_store, _waha_provider, _webhook_store, _agent

    # Create embedding function using Gemini
    from app.services.ai.google_gemini import GoogleGeminiProvider
    import numpy as np
    
    gemini_provider = GoogleGeminiProvider()
    
    async def embedding_fn(text: str) -> np.ndarray:
        """Generate embeddings using Gemini."""
        from google import genai
        settings = get_settings()
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        result = await client.aio.models.embed_content(
            model="models/gemini-embedding-001",
            contents=text,
        )
        return np.array(result.embeddings[0].values, dtype=np.float32)

    _redis_cache = RedisCacheProvider(embedding_fn=embedding_fn)
    await _redis_cache.connect()

    _qdrant_store = QdrantVectorStore(embedding_fn=embedding_fn, vector_size=3072)
    await _qdrant_store.connect()

    _waha_provider = WAHAProvider()
    await _waha_provider.connect()

    _webhook_store = WebhookStore()
    await _webhook_store.connect()

    cache_service = SemanticCacheService(cache=_redis_cache)
    conversation = ConversationManager(store=_qdrant_store)

    _agent = AgentOrchestrator(
        ai_provider=get_ai_provider(),
        cache_service=cache_service,
        conversation=conversation,
        whatsapp=_waha_provider,
        webhooks=_webhook_store,
    )

    logger.info("All services initialized")


async def shutdown_services() -> None:
    """Disconnect all services gracefully.

    Called during application shutdown (lifespan).
    """
    if _redis_cache:
        await _redis_cache.disconnect()
    if _qdrant_store:
        await _qdrant_store.disconnect()
    if _waha_provider:
        await _waha_provider.disconnect()
    if _webhook_store:
        await _webhook_store.disconnect()

    logger.info("All services disconnected")


def get_ai_provider() -> AIProvider:
    """Return the AI provider instance.

    Lazily imports to avoid loading the Gemini SDK
    until it is actually needed.
    """
    from app.services.ai.google_gemini import GoogleGeminiProvider
    return GoogleGeminiProvider()


def get_cache_provider() -> CacheProvider:
    """Return the cache provider singleton."""
    assert _redis_cache is not None, "Services not initialized"
    return _redis_cache


def get_vector_store() -> VectorStoreProvider:
    """Return the vector store singleton."""
    assert _qdrant_store is not None, "Services not initialized"
    return _qdrant_store


def get_whatsapp_provider() -> WhatsAppProvider:
    """Return the WhatsApp provider singleton."""
    assert _waha_provider is not None, "Services not initialized"
    return _waha_provider


def get_webhook_dispatcher() -> WebhookDispatcher:
    """Return the webhook dispatcher singleton."""
    assert _webhook_store is not None, "Services not initialized"
    return _webhook_store


def get_webhook_store() -> WebhookStore:
    """Return the webhook store (concrete type for audit endpoints)."""
    assert _webhook_store is not None, "Services not initialized"
    return _webhook_store


def get_agent() -> AgentOrchestrator:
    """Return the agent orchestrator singleton."""
    assert _agent is not None, "Services not initialized"
    return _agent
