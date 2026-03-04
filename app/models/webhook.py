"""Pydantic models for webhook payloads and delivery tracking."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class WebhookEvent(str, Enum):
    """Supported webhook event types."""

    MESSAGE_RECEIVED = "message_received"
    ESCALATION_TRIGGERED = "escalation_triggered"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"


class WebhookPayload(BaseModel):
    """Outbound webhook event payload.

    Attributes:
        event: Type of event that occurred.
        tenant_id: Tenant that originated the event.
        timestamp: When the event occurred (UTC).
        data: Event-specific data.
    """

    event: WebhookEvent
    tenant_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, object] = Field(default_factory=dict)


class DeliveryStatus(str, Enum):
    """Webhook delivery attempt status."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


class WebhookDelivery(BaseModel):
    """Tracks the delivery status of a dispatched webhook.

    Attributes:
        payload: The webhook payload that was dispatched.
        endpoint: Target URL the webhook was sent to.
        status: Current delivery status.
        attempts: Number of delivery attempts made.
        last_attempt_at: Timestamp of the most recent attempt.
        response_status_code: HTTP status code from the last attempt.
    """

    payload: WebhookPayload
    endpoint: str
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempts: int = 0
    last_attempt_at: datetime | None = None
    response_status_code: int | None = None
