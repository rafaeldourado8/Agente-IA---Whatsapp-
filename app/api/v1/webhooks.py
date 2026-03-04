"""WhatsApp webhook receiver endpoint.

Receives incoming messages from the WAHA webhook,
identifies the tenant, and processes the message through
the agent orchestrator.

Features:
- Message deduplication (prevents WAHA retry storms)
- Background processing (returns 200 immediately)
- Per-session locks (prevents message interleaving)

Supports both:
- POST /webhook/waha — native WAHA event payload (production)
- POST /webhook/message — simplified schema (testing/manual)
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.dependencies import get_agent, get_webhook_store
from app.core.exceptions import (
    AgentException,
    TenantNotFoundError,
)
from app.models.message import MessageType
from app.models.webhook import WebhookEvent, WebhookPayload
from app.tenant.loader import load_tenant

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])

# ------------------------------------------------------------------
# Deduplication cache (in-memory, TTL-based)
# ------------------------------------------------------------------
_DEDUP_TTL_SECONDS = 120  # Ignore duplicates within 2 minutes
_DEDUP_MAX_SIZE = 5000     # Max tracked message IDs
_processed_ids: OrderedDict[str, float] = OrderedDict()

# Per-session locks to prevent message interleaving
_session_locks: dict[str, asyncio.Lock] = {}


def _is_duplicate(message_id: str) -> bool:
    """Check if a message ID was already processed recently."""
    now = time.monotonic()

    # Clean expired entries
    expired = [
        mid for mid, ts in _processed_ids.items()
        if now - ts > _DEDUP_TTL_SECONDS
    ]
    for mid in expired:
        _processed_ids.pop(mid, None)

    # Evict oldest if too many
    while len(_processed_ids) >= _DEDUP_MAX_SIZE:
        _processed_ids.popitem(last=False)

    if message_id in _processed_ids:
        return True

    _processed_ids[message_id] = now
    return False


def _get_session_lock(session_id: str) -> asyncio.Lock:
    """Get or create a per-session lock."""
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


class IncomingMessage(BaseModel):
    """Schema for incoming WhatsApp message from WAHA.

    Attributes:
        instance: WAHA session name (mapped to tenant).
        phone: Sender phone number.
        message: Message text content.
        session_id: Conversation session identifier.
    """

    instance: str
    phone: str
    message: str
    session_id: str = Field(default="")


class MessageResponse(BaseModel):
    """Schema for the webhook response.

    Attributes:
        status: Processing result status.
        response: Agent's response text.
        source: Where the response came from (cache/ai/system).
        cached: Whether the response was served from cache.
    """

    status: str = "ok"
    response: str = ""
    source: str = ""
    cached: bool = False


# ------------------------------------------------------------------
# WAHA native webhook (production)
# ------------------------------------------------------------------


@router.post(
    "/webhook/waha",
    response_model=MessageResponse,
    summary="Receive WAHA native webhook event",
    response_description="Acknowledged — processing happens in background",
)
async def receive_waha_event(
    request: Request,
) -> MessageResponse:
    """Process an incoming WAHA webhook event.

    Returns 200 immediately and processes the message in the background.
    Duplicate messages (WAHA retries) are detected and ignored.
    """
    body = await request.json()
    event = body.get("event", "")
    session = body.get("session", "default")
    payload_data = body.get("payload", {})

    logger.info(
        "WAHA webhook received: event=%s session=%s",
        event,
        session,
    )

    # Only process incoming messages (not our own)
    if event != "message":
        return MessageResponse(status="ignored", response="event not handled")

    if payload_data.get("fromMe", False):
        return MessageResponse(status="ignored", response="own message")

    # Deduplication — extract message ID
    message_id = payload_data.get("id", "")
    if not message_id:
        message_id = (
            payload_data.get("_data", {})
            .get("id", {})
            .get("_serialized", "")
        )

    if message_id and _is_duplicate(message_id):
        logger.info("Duplicate message ignored: id=%s", message_id)
        return MessageResponse(status="ignored", response="duplicate")

    # Extract phone number
    raw_from = payload_data.get("from", "")
    phone = raw_from.split("@")[0] if "@" in raw_from else raw_from
    message_text = payload_data.get("body", "")

    logger.info(
        "Processing message: id=%s type=%s hasMedia=%s from=%s",
        message_id[:20] if message_id else "?",
        payload_data.get("_data", {}).get("type") or payload_data.get("type"),
        payload_data.get("hasMedia"),
        raw_from,
    )

    # Detect message type and media
    message_type = MessageType.TEXT
    media_url = None
    msg_type = (
        payload_data.get("_data", {}).get("type")
        or payload_data.get("type", "")
    )

    if payload_data.get("hasMedia"):
        if msg_type == "image":
            message_type = MessageType.IMAGE
            media_url = (
                payload_data.get("media", {}).get("url")
                or payload_data.get("mediaUrl")
            )
            message_text = payload_data.get("caption", "")
        elif msg_type in ["audio", "ptt"]:
            message_type = MessageType.AUDIO
            media_url = (
                payload_data.get("media", {}).get("url")
                or payload_data.get("mediaUrl")
            )
            message_text = "[Áudio recebido]"

    if not phone:
        return MessageResponse(status="ignored", response="empty phone")

    tenant_id = session
    session_id = f"{phone}_{tenant_id}"

    # Process in background — return 200 immediately to WAHA
    asyncio.create_task(
        _process_in_background(
            tenant_id=tenant_id,
            phone=raw_from,
            message=message_text,
            session_id=session_id,
            message_type=message_type,
            media_url=media_url,
        )
    )

    return MessageResponse(status="accepted", response="processing")


# ------------------------------------------------------------------
# Simplified webhook (testing / manual)
# ------------------------------------------------------------------


@router.post(
    "/webhook/message",
    response_model=MessageResponse,
    summary="Receive WhatsApp message (simplified)",
    response_description="Agent's response to the incoming message",
)
async def receive_message(
    payload: IncomingMessage,
    request: Request,
) -> MessageResponse:
    """Process an incoming WhatsApp message (synchronous, for testing)."""
    tenant_id = payload.instance
    session_id = payload.session_id or f"{payload.phone}_{tenant_id}"

    return await _process_incoming(
        tenant_id=tenant_id,
        phone=payload.phone,
        message=payload.message,
        session_id=session_id,
    )


# ------------------------------------------------------------------
# Background + shared processing logic
# ------------------------------------------------------------------


async def _process_in_background(
    tenant_id: str,
    phone: str,
    message: str,
    session_id: str,
    message_type: MessageType = MessageType.TEXT,
    media_url: str | None = None,
) -> None:
    """Process a message in background with per-session locking."""
    lock = _get_session_lock(session_id)

    async with lock:
        try:
            await _process_incoming(
                tenant_id=tenant_id,
                phone=phone,
                message=message,
                session_id=session_id,
                message_type=message_type,
                media_url=media_url,
            )
        except Exception as exc:
            logger.error(
                "Background processing failed: session=%s error=%s",
                session_id, exc,
            )


async def _process_incoming(
    tenant_id: str,
    phone: str,
    message: str,
    session_id: str,
    message_type: MessageType = MessageType.TEXT,
    media_url: str | None = None,
) -> MessageResponse:
    """Common handler for both WAHA and simplified webhook endpoints."""
    # Persist received webhook
    webhook_store = get_webhook_store()
    webhook_store.persist_received(
        WebhookPayload(
            event=WebhookEvent.MESSAGE_RECEIVED,
            tenant_id=tenant_id,
            data={
                "phone": phone,
                "message": message,
                "session_id": session_id,
            },
        )
    )

    try:
        settings = load_tenant(tenant_id)
    except TenantNotFoundError as exc:
        logger.warning("Tenant not found: %s", tenant_id)
        raise HTTPException(
            status_code=404,
            detail=f"Tenant '{tenant_id}' not found",
        ) from exc

    try:
        agent = get_agent()
        response = await agent.process_message(
            tenant_id=tenant_id,
            session_id=session_id,
            phone=phone,
            text=message,
            settings=settings,
            message_type=message_type,
            media_url=media_url,
        )

        logger.info(
            "Message processed: tenant=%s phone=%s source=%s cached=%s",
            tenant_id,
            phone,
            response.source.value,
            response.cached,
        )

        return MessageResponse(
            response=response.content,
            source=response.source.value,
            cached=response.cached,
        )

    except AgentException as exc:
        logger.error(
            "Agent error: tenant=%s error=%s",
            tenant_id,
            exc.message,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to process message",
        ) from exc
