"""Evolution API client for WhatsApp message delivery.

Wraps the Evolution API v2 REST interface to send and receive
WhatsApp messages. Each instance is configured for a specific
Evolution API server.
"""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.core.exceptions import WhatsAppDeliveryError
from app.core.interfaces import WhatsAppProvider

logger = logging.getLogger(__name__)


class EvolutionAPIProvider(WhatsAppProvider):
    """WhatsApp provider backed by Evolution API.

    Attributes:
        _base_url: Evolution API server URL.
        _api_key: Authentication key for the API.
        _client: Async HTTP client for making requests.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.EVOLUTION_API_URL).rstrip("/")
        self._api_key = api_key or settings.EVOLUTION_API_KEY
        self._client = client

    async def connect(self) -> None:
        """Initialize the HTTP client if not already provided."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._build_headers(),
                timeout=httpx.Timeout(30.0),
            )

    async def disconnect(self) -> None:
        """Close the HTTP client connection."""
        if self._client is not None:
            await self._client.aclose()

    async def send_message(
        self,
        phone: str,
        text: str,
        instance_name: str = "default",
    ) -> None:
        """Send a text message to a WhatsApp number.

        Args:
            phone: Recipient phone in international format (e.g. 5511999999999).
            text: Message body text.
            instance_name: Evolution API instance name.

        Raises:
            WhatsAppDeliveryError: If the API call fails.
        """
        assert self._client is not None

        endpoint = f"/message/sendText/{instance_name}"
        payload = {
            "number": phone,
            "text": text,
        }

        response = await self._post(endpoint, payload)
        logger.info(
            "Message sent: phone=%s instance=%s status=%d",
            phone,
            instance_name,
            response.status_code,
        )

    async def health_check(self) -> bool:
        """Check if the Evolution API server is reachable.

        Returns:
            True if the server responds successfully.
        """
        try:
            assert self._client is not None
            response = await self._client.get("/instance/fetchInstances")
            return response.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_headers(self) -> dict[str, str]:
        """Build the authentication headers."""
        return {
            "apikey": self._api_key,
            "Content-Type": "application/json",
        }

    async def _post(
        self,
        endpoint: str,
        payload: dict[str, object],
    ) -> httpx.Response:
        """Execute a POST request with error handling.

        Args:
            endpoint: API endpoint path.
            payload: JSON body.

        Returns:
            The httpx Response.

        Raises:
            WhatsAppDeliveryError: On HTTP or network errors.
        """
        assert self._client is not None

        try:
            response = await self._client.post(endpoint, json=payload)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            raise WhatsAppDeliveryError(
                f"Evolution API error {exc.response.status_code}: "
                f"{exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise WhatsAppDeliveryError(
                f"Evolution API connection error: {exc}"
            ) from exc
