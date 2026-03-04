"""Semantic cache orchestration layer.

Coordinates between the CacheProvider (Redis) and the embedding
function to provide a clean caching interface for the agent.
This module handles the decision logic (hit/miss) while the
actual storage is delegated to the CacheProvider.
"""

from __future__ import annotations

import logging

from app.core.interfaces import CacheProvider
from app.models.response import AgentResponse, ResponseSource

logger = logging.getLogger(__name__)


class SemanticCacheService:
    """Orchestrates semantic cache lookups and writes.

    Acts as the bridge between the agent and the cache provider,
    handling cache-hit responses and cache-miss storage.

    Attributes:
        _cache: Cache provider implementation.
    """

    def __init__(self, cache: CacheProvider) -> None:
        self._cache = cache

    async def try_cache(
        self,
        query: str,
        threshold: float,
        tenant_id: str,
    ) -> AgentResponse | None:
        """Attempt to serve a response from the semantic cache.

        Args:
            query: User message to search for.
            threshold: Minimum similarity for a cache hit.
            tenant_id: Tenant namespace.

        Returns:
            AgentResponse if a cache hit is found, otherwise None.
        """
        # Skip cache for empty queries
        if not query or not query.strip():
            logger.debug("Skipping cache for empty query")
            return None
            
        cached = await self._cache.get_semantic(
            query=query,
            threshold=threshold,
            tenant_id=tenant_id,
        )

        if cached is not None:
            logger.info(
                "Cache HIT: tenant=%s query_preview='%s'",
                tenant_id,
                query[:50],
            )
            return AgentResponse(
                content=cached,
                source=ResponseSource.CACHE,
                cached=True,
                latency_ms=0.0,
                tokens_used=0,
            )

        logger.debug(
            "Cache MISS: tenant=%s query_preview='%s'",
            tenant_id,
            query[:50],
        )
        return None

    async def store(
        self,
        query: str,
        response: str,
        ttl_hours: int,
        tenant_id: str,
    ) -> None:
        """Store a query-response pair in the cache.

        Args:
            query: Original user query.
            response: AI-generated response to cache.
            ttl_hours: Cache lifetime in hours.
            tenant_id: Tenant namespace.
        """
        # Skip storing empty queries
        if not query or not query.strip():
            logger.debug("Skipping cache storage for empty query")
            return
            
        ttl_seconds = ttl_hours * 3600

        await self._cache.set(
            query=query,
            response=response,
            ttl=ttl_seconds,
            tenant_id=tenant_id,
        )

        logger.debug(
            "Cached response: tenant=%s ttl=%dh",
            tenant_id,
            ttl_hours,
        )
