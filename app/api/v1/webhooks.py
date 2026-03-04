"""WhatsApp webhook receiver endpoint.

Receives incoming messages from the Evolution API webhook,
identifies the tenant, and processes the message through
the agent orchestrator.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.dependencies import get_agent, get_webhook_store
from app.core.exceptions import (
    AgentException,
    TenantNotFoundError,
)
from app.models.webhook import WebhookEvent, WebhookPayload
from app.tenant.loader import load_tenant

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


class IncomingMessage(BaseModel):
    """Schema for incoming WhatsApp message from Evolution API.

    Attributes:
        instance: Evolution API instance name (mapped to tenant).
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
    response: str
    source: str
    cached: bool


@router.post(
    "/webhook/message",
    response_model=MessageResponse,
    summary="Receive WhatsApp message",
    response_description="Agent's response to the incoming message",
)
async def receive_message(
    payload: IncomingMessage,
    request: Request,
) -> MessageResponse:
    """Process an incoming WhatsApp message.

    The ``instance`` field maps to the tenant_id. The message
    is processed through the full agent pipeline (cache → AI →
    history → webhook → response).

    Args:
        payload: Incoming message data from Evolution API.
        request: FastAPI request object.

    Returns:
        The agent's response with metadata.

    Raises:
        HTTPException 404: If the tenant is not found.
        HTTPException 500: If processing fails.
    """
    tenant_id = payload.instance
    session_id = payload.session_id or f"{payload.phone}_{tenant_id}"

    # Persist received webhook
    webhook_store = get_webhook_store()
    webhook_store.persist_received(
        WebhookPayload(
            event=WebhookEvent.MESSAGE_RECEIVED,
            tenant_id=tenant_id,
            data={
                "phone": payload.phone,
                "message": payload.message,
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
            phone=payload.phone,
            text=payload.message,
            settings=settings,
        )

        logger.info(
            "Message processed: tenant=%s phone=%s source=%s cached=%s",
            tenant_id,
            payload.phone,
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
