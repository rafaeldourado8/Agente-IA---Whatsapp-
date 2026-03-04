"""WAHA (WhatsApp HTTP API) client for WhatsApp message delivery.

Wraps the WAHA REST interface to send and receive
WhatsApp messages. Each instance is configured for a specific
WAHA server.

Docs: https://waha.devlike.pro/docs/how-to/send-messages/
"""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.core.exceptions import WhatsAppDeliveryError
from app.core.interfaces import WhatsAppProvider

logger = logging.getLogger(__name__)


class WAHAProvider(WhatsAppProvider):
    """WhatsApp provider backed by WAHA (WhatsApp HTTP API).

    Attributes:
        _base_url: WAHA server URL.
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
        self._base_url = (base_url or settings.WAHA_API_URL).rstrip("/")
        self._api_key = api_key or settings.WAHA_API_KEY
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
            instance_name: WAHA session name.

        Raises:
            WhatsAppDeliveryError: If the API call fails.
        """
        assert self._client is not None

        # WAHA expects chatId in the format "number@c.us"
        chat_id = f"{phone}@c.us" if "@" not in phone else phone

        endpoint = "/api/sendText"
        payload = {
            "session": instance_name,
            "chatId": chat_id,
            "text": text,
        }

        response = await self._post(endpoint, payload)
        logger.info(
            "Message sent: phone=%s session=%s status=%d",
            phone,
            instance_name,
            response.status_code,
        )

    async def health_check(self) -> bool:
        """Check if the WAHA server is reachable.

        Returns:
            True if the server responds successfully.
        """
        try:
            assert self._client is not None
            response = await self._client.get("/api/sessions/")
            return response.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_headers(self) -> dict[str, str]:
        """Build the authentication headers."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["X-Api-Key"] = self._api_key
        return headers

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
                f"WAHA API error {exc.response.status_code}: "
                f"{exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise WhatsAppDeliveryError(
                f"WAHA API connection error: {exc}"
            ) from exc
