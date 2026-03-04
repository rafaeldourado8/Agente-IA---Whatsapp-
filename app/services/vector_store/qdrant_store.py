"""Qdrant-based vector store for conversation history.

Stores messages as vector points in Qdrant, enabling both
chronological retrieval (by session) and semantic search
across conversation history.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import get_settings
from app.core.interfaces import VectorStoreProvider
from app.models.message import Message, MessageRole

logger = logging.getLogger(__name__)


class QdrantVectorStore(VectorStoreProvider):
    """Conversation history storage backed by Qdrant.

    Each message is stored as a Qdrant point with:
    - Vector: embedding of the message content
    - Payload: tenant_id, session_id, role, content, timestamp

    Attributes:
        _client: Async Qdrant client.
        _collection: Name of the Qdrant collection.
        _vector_size: Dimensionality of embedding vectors.
        _embedding_fn: Async callable that converts text to list[float].
    """

    def __init__(
        self,
        client: AsyncQdrantClient | None = None,
        collection_name: str | None = None,
        vector_size: int = 768,
        embedding_fn: object = None,
    ) -> None:
        self._client = client
        settings = get_settings()
        self._collection = collection_name or settings.QDRANT_COLLECTION_NAME
        self._vector_size = vector_size
        self._embedding_fn = embedding_fn

    async def connect(self) -> None:
        """Initialize the Qdrant client and ensure collection exists."""
        if self._client is None:
            settings = get_settings()
            self._client = AsyncQdrantClient(url=settings.QDRANT_URL)

        await self._ensure_collection()

    async def disconnect(self) -> None:
        """Close the Qdrant client connection."""
        if self._client is not None:
            await self._client.close()

    async def store_message(
        self,
        tenant_id: str,
        session_id: str,
        message: Message,
    ) -> None:
        """Persist a message in the vector store.

        Args:
            tenant_id: Identifier of the tenant.
            session_id: Identifier of the conversation session.
            message: The message to store.
        """
        assert self._client is not None

        embedding = await self._get_embedding(message.content)
        point_id = str(uuid.uuid4())

        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "tenant_id": tenant_id,
                "session_id": session_id,
                "role": message.role.value,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "metadata": message.metadata,
            },
        )

        await self._client.upsert(
            collection_name=self._collection,
            points=[point],
        )

        logger.debug(
            "Stored message in Qdrant: tenant=%s session=%s role=%s",
            tenant_id,
            session_id,
            message.role.value,
        )

    async def get_history(
        self,
        tenant_id: str,
        session_id: str,
        limit: int = 20,
    ) -> list[Message]:
        """Retrieve conversation history for a session.

        Messages are returned in chronological order (oldest first).

        Args:
            tenant_id: Identifier of the tenant.
            session_id: Identifier of the conversation session.
            limit: Maximum number of messages to retrieve.

        Returns:
            List of messages ordered by timestamp.
        """
        assert self._client is not None

        query_filter = Filter(
            must=[
                FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                FieldCondition(key="session_id", match=MatchValue(value=session_id)),
            ]
        )

        results = await self._client.scroll(
            collection_name=self._collection,
            scroll_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        points = results[0]
        messages = [self._point_to_message(point) for point in points]

        messages.sort(key=lambda m: m.timestamp)

        logger.debug(
            "Retrieved %d messages: tenant=%s session=%s",
            len(messages),
            tenant_id,
            session_id,
        )
        return messages

    async def search_similar(
        self,
        tenant_id: str,
        query: str,
        limit: int = 5,
    ) -> list[Message]:
        """Find messages semantically similar to a query across all sessions.

        Useful for enriching context with relevant past conversations.

        Args:
            tenant_id: Tenant scope for the search.
            query: Text to find similar messages for.
            limit: Maximum number of results.

        Returns:
            List of similar messages, highest similarity first.
        """
        assert self._client is not None

        embedding = await self._get_embedding(query)

        results = await self._client.search(
            collection_name=self._collection,
            query_vector=embedding,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="tenant_id",
                        match=MatchValue(value=tenant_id),
                    ),
                ]
            ),
            limit=limit,
            with_payload=True,
        )

        return [self._point_to_message(point) for point in results]

    async def health_check(self) -> bool:
        """Check if Qdrant is reachable.

        Returns:
            True if the collection exists and is accessible.
        """
        try:
            assert self._client is not None
            info = await self._client.get_collection(self._collection)
            return info is not None
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _ensure_collection(self) -> None:
        """Create the collection if it doesn't already exist."""
        assert self._client is not None

        collections = await self._client.get_collections()
        existing = [c.name for c in collections.collections]

        if self._collection not in existing:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection: %s", self._collection)

    async def _get_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""
        if self._embedding_fn is None:
            raise RuntimeError("No embedding function configured")
        result = await self._embedding_fn(text)
        if hasattr(result, "tolist"):
            return result.tolist()
        return list(result)

    @staticmethod
    def _point_to_message(point: object) -> Message:
        """Convert a Qdrant point/scored point to a Message model."""
        payload = point.payload  # type: ignore[attr-defined]
        return Message(
            role=MessageRole(payload["role"]),
            content=payload["content"],
            timestamp=datetime.fromisoformat(payload["timestamp"]),
            metadata=payload.get("metadata", {}),
        )
