"""Conversation history management.

Handles storing new messages and assembling conversation context
for the AI provider. Retrieves history from the vector store
and formats it for inclusion in the AI prompt.
"""

from __future__ import annotations

import logging

from app.core.interfaces import VectorStoreProvider
from app.models.message import Message

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation history for agent sessions.

    Coordinates with the VectorStoreProvider to persist messages
    and retrieve contextual history for AI prompts.

    Attributes:
        _store: Vector store implementation for message persistence.
        _max_history: Maximum messages to include as context.
    """

    def __init__(
        self,
        store: VectorStoreProvider,
        max_history: int = 20,
    ) -> None:
        self._store = store
        self._max_history = max_history

    async def add_message(
        self,
        tenant_id: str,
        session_id: str,
        message: Message,
    ) -> None:
        """Store a message in the conversation history.

        Args:
            tenant_id: Tenant identifier.
            session_id: Session identifier.
            message: Message to persist.
        """
        await self._store.store_message(
            tenant_id=tenant_id,
            session_id=session_id,
            message=message,
        )

        logger.debug(
            "Message stored: tenant=%s session=%s role=%s",
            tenant_id,
            session_id,
            message.role.value,
        )

    async def get_context(
        self,
        tenant_id: str,
        session_id: str,
    ) -> list[Message]:
        """Retrieve conversation context for an AI prompt.

        Returns the most recent messages for the given session,
        ordered chronologically (oldest first).

        Args:
            tenant_id: Tenant identifier.
            session_id: Session identifier.

        Returns:
            Ordered list of messages for context.
        """
        messages = await self._store.get_history(
            tenant_id=tenant_id,
            session_id=session_id,
            limit=self._max_history,
        )

        logger.debug(
            "Context retrieved: tenant=%s session=%s messages=%d",
            tenant_id,
            session_id,
            len(messages),
        )

        return messages
