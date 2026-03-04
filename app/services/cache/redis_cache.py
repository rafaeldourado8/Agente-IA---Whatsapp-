"""Redis-based semantic cache implementation.

Uses Redis to store query-response pairs with embedding vectors
for semantic similarity matching. Each tenant's cache is isolated
by key namespacing.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import numpy as np
import redis.asyncio as redis

from app.config import get_settings
from app.core.exceptions import CacheOperationError
from app.core.interfaces import CacheProvider

logger = logging.getLogger(__name__)


class RedisCacheProvider(CacheProvider):
    """Semantic cache backed by Redis.

    Stores query embeddings and responses in Redis. On lookup,
    computes cosine similarity between the incoming query embedding
    and all cached embeddings for the tenant, returning the best
    match if it exceeds the threshold.

    Attributes:
        _client: Async Redis client instance.
        _embedding_fn: Callable that converts text to a numpy array.
    """

    def __init__(
        self,
        client: redis.Redis | None = None,
        embedding_fn: Any = None,
    ) -> None:
        self._client = client
        self._embedding_fn = embedding_fn

    async def connect(self) -> None:
        """Initialize the Redis connection if not already provided."""
        if self._client is None:
            settings = get_settings()
            self._client = redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
            )

    async def disconnect(self) -> None:
        """Close the Redis connection gracefully."""
        if self._client is not None:
            await self._client.aclose()

    async def get_semantic(
        self,
        query: str,
        threshold: float,
        tenant_id: str = "default",
    ) -> str | None:
        """Find a cached response semantically similar to the query.

        Args:
            query: User query to match.
            threshold: Minimum cosine similarity (0.0–1.0).
            tenant_id: Tenant namespace for cache isolation.

        Returns:
            Cached response text if similarity >= threshold, else None.
        """
        try:
            return await self._search_cache(query, threshold, tenant_id)
        except Exception as exc:
            raise CacheOperationError(
                f"Cache lookup failed for tenant '{tenant_id}': {exc}"
            ) from exc

    async def set(
        self,
        query: str,
        response: str,
        ttl: int,
        tenant_id: str = "default",
    ) -> None:
        """Store a query-response pair in the semantic cache.

        Args:
            query: The original user query.
            response: AI-generated response to cache.
            ttl: Time-to-live in seconds.
            tenant_id: Tenant namespace for cache isolation.
        """
        # Skip caching if no embedding function
        if self._embedding_fn is None:
            logger.warning("Skipping cache write: no embedding function configured")
            return
            
        try:
            await self._store_entry(query, response, ttl, tenant_id)
        except Exception as exc:
            logger.warning("Cache write failed for tenant '%s': %s", tenant_id, exc)
            # Don't raise - allow the request to continue without caching

    async def clear_tenant(self, tenant_id: str) -> int:
        """Remove all cached entries for a specific tenant.

        Args:
            tenant_id: Tenant whose cache to clear.

        Returns:
            Number of entries removed.
        """
        assert self._client is not None
        pattern = f"cache:{tenant_id}:*"
        keys = []
        async for key in self._client.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            await self._client.delete(*keys)

        logger.info("Cleared %d cache entries for tenant '%s'", len(keys), tenant_id)
        return len(keys)

    async def health_check(self) -> bool:
        """Check if Redis is reachable.

        Returns:
            True if Redis responds to PING.
        """
        try:
            assert self._client is not None
            return await self._client.ping()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _search_cache(
        self,
        query: str,
        threshold: float,
        tenant_id: str,
    ) -> str | None:
        """Search cached entries for a semantic match."""
        assert self._client is not None

        if self._embedding_fn is None:
            return None

        query_embedding = await self._get_embedding(query)
        index_key = f"cache_index:{tenant_id}"

        entry_keys = await self._client.smembers(index_key)
        if not entry_keys:
            return None

        best_score = -1.0
        best_response: str | None = None

        for entry_key in entry_keys:
            raw = await self._client.get(entry_key)
            if raw is None:
                await self._client.srem(index_key, entry_key)
                continue

            entry = json.loads(raw)
            cached_embedding = np.array(entry["embedding"], dtype=np.float32)
            score = self._cosine_similarity(query_embedding, cached_embedding)

            if score >= threshold and score > best_score:
                best_score = score
                best_response = entry["response"]

        if best_response is not None:
            logger.info(
                "Cache HIT for tenant '%s' (score=%.4f)",
                tenant_id,
                best_score,
            )

        return best_response

    async def _store_entry(
        self,
        query: str,
        response: str,
        ttl: int,
        tenant_id: str,
    ) -> None:
        """Store a new cache entry with its embedding."""
        assert self._client is not None

        # Skip caching if no embedding function
        if self._embedding_fn is None:
            logger.warning("Skipping cache write: no embedding function configured")
            return

        embedding = await self._get_embedding(query)
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        entry_key = f"cache:{tenant_id}:{query_hash}"
        index_key = f"cache_index:{tenant_id}"

        entry = {
            "query": query,
            "response": response,
            "embedding": embedding.tolist(),
        }

        await self._client.set(entry_key, json.dumps(entry), ex=ttl)
        await self._client.sadd(index_key, entry_key)

        logger.debug("Cached response for tenant '%s': key=%s", tenant_id, entry_key)

    async def _get_embedding(self, text: str) -> np.ndarray:
        """Generate an embedding vector for the given text."""
        if self._embedding_fn is None:
            raise CacheOperationError("No embedding function configured")
        return await self._embedding_fn(text)

    @staticmethod
    def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot / (norm_a * norm_b))
