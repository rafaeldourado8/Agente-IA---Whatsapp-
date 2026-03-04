"""Webhook event persistence and dispatching.

Stores all received and sent webhook events with full payloads
for auditability. Dispatches outbound webhooks with HMAC signing
and retry logic.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime

import httpx

from app.core.exceptions import WebhookDispatchError
from app.core.interfaces import WebhookDispatcher
from app.models.webhook import (
    DeliveryStatus,
    WebhookDelivery,
    WebhookPayload,
)

logger = logging.getLogger(__name__)


class WebhookStore(WebhookDispatcher):
    """Webhook dispatcher with persistence and retry.

    Persists every webhook event (received and sent) in memory
    for auditability. In production, this should be backed by
    a persistent store (Redis, database, etc.).

    Attributes:
        _client: Async HTTP client for outbound webhook delivery.
        _received: Log of received webhook payloads.
        _deliveries: Log of outbound delivery attempts.
        _max_retries: Maximum retry attempts for failed deliveries.
    """

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        max_retries: int = 3,
    ) -> None:
        self._client = client
        self._max_retries = max_retries
        self._received: list[WebhookPayload] = []
        self._deliveries: list[WebhookDelivery] = []

    async def connect(self) -> None:
        """Initialize the HTTP client if not already provided."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0),
            )

    async def disconnect(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()

    def persist_received(self, payload: WebhookPayload) -> None:
        """Store a received webhook event for auditing.

        Args:
            payload: The incoming webhook payload.
        """
        self._received.append(payload)
        logger.info(
            "Persisted received webhook: event=%s tenant=%s",
            payload.event,
            payload.tenant_id,
        )

    async def dispatch(
        self,
        event: str,
        payload: dict[str, object],
        endpoint: str,
        secret: str,
    ) -> bool:
        """Dispatch a webhook event to the configured endpoint.

        Includes HMAC-SHA256 signature in the ``X-Webhook-Signature``
        header. Retries on failure up to ``max_retries`` times.

        Args:
            event: Event type name.
            payload: Event data.
            endpoint: Target URL.
            secret: HMAC signing secret.

        Returns:
            True if delivery succeeded.
        """
        body = json.dumps(payload, default=str, sort_keys=True)
        signature = self._compute_signature(body, secret)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event,
            "X-Webhook-Signature": signature,
        }

        delivery = WebhookDelivery(
            payload=WebhookPayload(
                event=event,  # type: ignore[arg-type]
                tenant_id=payload.get("tenant_id", "unknown"),  # type: ignore[arg-type]
                data=payload,
            ),
            endpoint=endpoint,
        )

        success = await self._deliver_with_retry(
            endpoint, body, headers, delivery
        )

        self._deliveries.append(delivery)
        return success

    def get_received(
        self,
        tenant_id: str | None = None,
        limit: int = 50,
    ) -> list[WebhookPayload]:
        """Retrieve persisted received webhooks.

        Args:
            tenant_id: Filter by tenant (optional).
            limit: Maximum number of results.

        Returns:
            List of webhook payloads, most recent first.
        """
        results = self._received
        if tenant_id is not None:
            results = [r for r in results if r.tenant_id == tenant_id]
        return list(reversed(results[-limit:]))

    def get_deliveries(
        self,
        tenant_id: str | None = None,
        limit: int = 50,
    ) -> list[WebhookDelivery]:
        """Retrieve persisted outbound delivery records.

        Args:
            tenant_id: Filter by tenant (optional).
            limit: Maximum number of results.

        Returns:
            List of delivery records, most recent first.
        """
        results = self._deliveries
        if tenant_id is not None:
            results = [
                d for d in results
                if d.payload.tenant_id == tenant_id
            ]
        return list(reversed(results[-limit:]))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _deliver_with_retry(
        self,
        endpoint: str,
        body: str,
        headers: dict[str, str],
        delivery: WebhookDelivery,
    ) -> bool:
        """Attempt delivery with retries on failure."""
        assert self._client is not None

        for attempt in range(1, self._max_retries + 1):
            delivery.attempts = attempt
            delivery.last_attempt_at = datetime.utcnow()

            try:
                response = await self._client.post(
                    endpoint,
                    content=body,
                    headers=headers,
                )
                delivery.response_status_code = response.status_code

                if response.is_success:
                    delivery.status = DeliveryStatus.DELIVERED
                    logger.info(
                        "Webhook delivered: endpoint=%s attempt=%d",
                        endpoint,
                        attempt,
                    )
                    return True

                logger.warning(
                    "Webhook delivery failed (HTTP %d): endpoint=%s attempt=%d/%d",
                    response.status_code,
                    endpoint,
                    attempt,
                    self._max_retries,
                )

            except httpx.RequestError as exc:
                logger.warning(
                    "Webhook delivery error: endpoint=%s attempt=%d/%d error=%s",
                    endpoint,
                    attempt,
                    self._max_retries,
                    exc,
                )

        delivery.status = DeliveryStatus.FAILED
        logger.error(
            "Webhook delivery exhausted retries: endpoint=%s",
            endpoint,
        )
        return False

    @staticmethod
    def _compute_signature(body: str, secret: str) -> str:
        """Compute HMAC-SHA256 signature for the payload body.

        Args:
            body: JSON string to sign.
            secret: Shared secret key.

        Returns:
            Hex-encoded HMAC signature.
        """
        return hmac.new(
            key=secret.encode("utf-8"),
            msg=body.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
