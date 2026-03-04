"""Core domain interfaces (Abstract Base Classes).

All external dependencies are represented as abstractions here.
Concrete implementations live in `app/services/` and depend on these contracts,
never the other way around (Dependency Inversion Principle).
"""

from abc import ABC, abstractmethod

from app.models.message import Message
from app.models.response import AgentResponse


class AIProvider(ABC):
    """Contract for AI text-generation providers."""

    @abstractmethod
    async def generate_response(
        self,
        messages: list[Message],
        system_prompt: str,
    ) -> AgentResponse:
        """Generate an AI response given conversation history and a system prompt.

        Args:
            messages: Ordered conversation history.
            system_prompt: Tenant-specific system instructions.

        Returns:
            The generated response with metadata.
        """


class CacheProvider(ABC):
    """Contract for semantic cache storage."""

    @abstractmethod
    async def get_semantic(
        self,
        query: str,
        threshold: float,
    ) -> str | None:
        """Look up a semantically similar cached response.

        Args:
            query: The user query to match against cached entries.
            threshold: Minimum cosine similarity for a cache hit (0.0–1.0).

        Returns:
            Cached response text if a match is found, otherwise None.
        """

    @abstractmethod
    async def set(
        self,
        query: str,
        response: str,
        ttl: int,
    ) -> None:
        """Store a query–response pair in the semantic cache.

        Args:
            query: The original user query.
            response: The AI-generated response to cache.
            ttl: Time-to-live in seconds.
        """


class VectorStoreProvider(ABC):
    """Contract for conversation history storage backed by a vector database."""

    @abstractmethod
    async def store_message(
        self,
        tenant_id: str,
        session_id: str,
        message: Message,
    ) -> None:
        """Persist a single message in the vector store.

        Args:
            tenant_id: Identifier of the tenant.
            session_id: Identifier of the conversation session.
            message: The message to persist.
        """

    @abstractmethod
    async def get_history(
        self,
        tenant_id: str,
        session_id: str,
        limit: int = 20,
    ) -> list[Message]:
        """Retrieve recent conversation history for a session.

        Args:
            tenant_id: Identifier of the tenant.
            session_id: Identifier of the conversation session.
            limit: Maximum number of messages to retrieve.

        Returns:
            List of messages ordered chronologically.
        """


class WhatsAppProvider(ABC):
    """Contract for WhatsApp message delivery."""

    @abstractmethod
    async def send_message(
        self,
        phone: str,
        text: str,
    ) -> None:
        """Send a plain text message to a WhatsApp number.

        Args:
            phone: Recipient phone number in international format.
            text: Message body.
        """


class WebhookDispatcher(ABC):
    """Contract for dispatching webhook events to tenant endpoints."""

    @abstractmethod
    async def dispatch(
        self,
        event: str,
        payload: dict[str, object],
        endpoint: str,
        secret: str,
    ) -> bool:
        """Send a webhook event to the configured endpoint.

        Args:
            event: The event type name (e.g. ``message_received``).
            payload: Event data to serialize as JSON.
            endpoint: Target URL to POST the webhook to.
            secret: Shared secret for HMAC signature.

        Returns:
            True if the webhook was delivered successfully.
        """
