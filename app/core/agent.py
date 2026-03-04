"""Main agent orchestrator.

This is the central coordination point for processing user messages.
It follows the pipeline: business hours → escalation check →
semantic cache → AI generation → cache storage → history storage →
webhook dispatch.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.cache import SemanticCacheService
from app.core.conversation import ConversationManager
from app.core.interfaces import AIProvider, WebhookDispatcher, WhatsAppProvider
from app.models.message import Message, MessageRole, MessageType
from app.models.response import AgentResponse, ResponseSource
from app.tenant.models import TenantSettings

logger = logging.getLogger(__name__)

# Weekday mapping: Python's weekday() → schedule field
_WEEKDAY_SCHEDULE = {
    0: "monday_friday",  # Monday
    1: "monday_friday",
    2: "monday_friday",
    3: "monday_friday",
    4: "monday_friday",  # Friday
    5: "saturday",
    6: "sunday",
}


class AgentOrchestrator:
    """Central orchestrator that processes user messages.

    Coordinates all subsystems: cache, AI provider, conversation
    history, escalation, business hours, and webhooks.

    Attributes:
        _ai: AI text generation provider.
        _cache: Semantic cache service.
        _conversation: Conversation history manager.
        _whatsapp: WhatsApp delivery provider.
        _webhooks: Webhook event dispatcher.
    """

    def __init__(
        self,
        ai_provider: AIProvider,
        cache_service: SemanticCacheService,
        conversation: ConversationManager,
        whatsapp: WhatsAppProvider,
        webhooks: WebhookDispatcher,
    ) -> None:
        self._ai = ai_provider
        self._cache = cache_service
        self._conversation = conversation
        self._whatsapp = whatsapp
        self._webhooks = webhooks

    async def process_message(
        self,
        tenant_id: str,
        session_id: str,
        phone: str,
        text: str,
        settings: TenantSettings,
        message_type: MessageType = MessageType.TEXT,
        media_url: str | None = None,
    ) -> AgentResponse:
        """Process an incoming user message through the full pipeline.

        Pipeline:
        1. Check business hours → return out_of_hours_message if closed
        2. Check escalation keywords → trigger escalation if matched
        3. Try semantic cache → return cached response if hit (text only)
        4. Retrieve conversation history for context
        5. Call AI provider to generate response
        6. Store response in cache (text only)
        7. Persist messages in history
        8. Dispatch webhooks
        9. Send response via WhatsApp

        Args:
            tenant_id: Identifier of the tenant.
            session_id: Current conversation session ID.
            phone: User's WhatsApp phone number.
            text: User's message text.
            settings: Tenant configuration.
            message_type: Type of message (text, image, audio).
            media_url: URL to media file if applicable.

        Returns:
            The agent's response.
        """
        user_message = Message(
            role=MessageRole.USER,
            content=text,
            message_type=message_type,
            media_url=media_url,
        )

        # Step 1: Business hours check
        if not self._is_within_hours(settings):
            return await self._handle_out_of_hours(
                tenant_id, session_id, phone, user_message, settings
            )

        # Step 2: Escalation check
        if self._should_escalate(text, settings):
            return await self._handle_escalation(
                tenant_id, session_id, phone, user_message, settings
            )

        # Step 3: Semantic cache lookup (only for text messages)
        if message_type == MessageType.TEXT:
            cached = await self._cache.try_cache(
                query=text,
                threshold=settings.cache.semantic_threshold,
                tenant_id=tenant_id,
            )
            if cached is not None:
                await self._finalize(
                    tenant_id, session_id, phone,
                    user_message, cached, settings
                )
                return cached

        # Step 4: Retrieve conversation context
        history = await self._conversation.get_context(
            tenant_id=tenant_id,
            session_id=session_id,
        )

        # Step 5: Call AI provider
        all_messages = history + [user_message]
        response = await self._ai.generate_response(
            messages=all_messages,
            system_prompt=settings.agent.system_prompt,
        )

        # Step 6: Store in cache (only for text messages)
        if message_type == MessageType.TEXT:
            await self._cache.store(
                query=text,
                response=response.content,
                ttl_hours=settings.cache.ttl_hours,
                tenant_id=tenant_id,
            )

        # Steps 7–9: Finalize
        await self._finalize(
            tenant_id, session_id, phone,
            user_message, response, settings
        )

        return response

    async def _handle_out_of_hours(
        self,
        tenant_id: str,
        session_id: str,
        phone: str,
        user_message: Message,
        settings: TenantSettings,
    ) -> AgentResponse:
        """Return the out-of-hours message."""
        response = AgentResponse(
            content=settings.business_hours.out_of_hours_message,
            source=ResponseSource.SYSTEM,
            cached=False,
        )

        logger.info(
            "Out of hours: tenant=%s phone=%s",
            tenant_id, phone,
        )

        await self._finalize(
            tenant_id, session_id, phone,
            user_message, response, settings
        )
        return response

    async def _handle_escalation(
        self,
        tenant_id: str,
        session_id: str,
        phone: str,
        user_message: Message,
        settings: TenantSettings,
    ) -> AgentResponse:
        """Handle escalation to a human agent."""
        response = AgentResponse(
            content=settings.escalation.message,
            source=ResponseSource.SYSTEM,
            cached=False,
        )

        # Dispatch escalation webhook if configured
        if (
            settings.escalation.action == "webhook"
            and settings.escalation.webhook_url
        ):
            await self._webhooks.dispatch(
                event="escalation_triggered",
                payload={
                    "tenant_id": tenant_id,
                    "session_id": session_id,
                    "phone": phone,
                    "message": user_message.content,
                },
                endpoint=settings.escalation.webhook_url,
                secret=settings.webhooks.secret,
            )

        logger.info(
            "Escalation triggered: tenant=%s phone=%s",
            tenant_id, phone,
        )

        await self._finalize(
            tenant_id, session_id, phone,
            user_message, response, settings
        )
        return response

    async def _finalize(
        self,
        tenant_id: str,
        session_id: str,
        phone: str,
        user_message: Message,
        response: AgentResponse,
        settings: TenantSettings,
    ) -> None:
        """Persist messages, send response, and dispatch webhooks."""
        # Store user message in history
        await self._conversation.add_message(
            tenant_id=tenant_id,
            session_id=session_id,
            message=user_message,
        )

        # Store assistant response in history
        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=response.content,
        )
        await self._conversation.add_message(
            tenant_id=tenant_id,
            session_id=session_id,
            message=assistant_message,
        )

        # Send response via WhatsApp
        await self._whatsapp.send_message(
            phone=phone,
            text=response.content,
        )

        # Dispatch message_received webhook
        if settings.webhooks.endpoint:
            await self._webhooks.dispatch(
                event="message_received",
                payload={
                    "tenant_id": tenant_id,
                    "session_id": session_id,
                    "phone": phone,
                    "user_message": user_message.content,
                    "agent_response": response.content,
                    "source": response.source.value,
                    "cached": response.cached,
                },
                endpoint=settings.webhooks.endpoint,
                secret=settings.webhooks.secret,
            )

    @staticmethod
    def _is_within_hours(settings: TenantSettings) -> bool:
        """Check if the current time falls within business hours.

        Args:
            settings: Tenant configuration with schedule.

        Returns:
            True if currently within operating hours, or if
            no schedule is configured (always open).
        """
        schedule = settings.business_hours.schedule
        timezone_name = settings.business_hours.timezone

        try:
            tz = ZoneInfo(timezone_name)
        except KeyError:
            logger.warning("Invalid timezone: %s, defaulting to open", timezone_name)
            return True

        now = datetime.now(tz)
        weekday = now.weekday()
        schedule_key = _WEEKDAY_SCHEDULE[weekday]

        hours_str = getattr(schedule, schedule_key, None)
        if hours_str is None:
            return False

        return _is_time_in_range(now, hours_str)

    @staticmethod
    def _should_escalate(
        text: str, settings: TenantSettings
    ) -> bool:
        """Check if the message contains escalation keywords.

        Args:
            text: User message text.
            settings: Tenant configuration.

        Returns:
            True if any escalation keyword is found.
        """
        text_lower = text.lower()
        return any(
            keyword.lower() in text_lower
            for keyword in settings.escalation.trigger_keywords
        )


def _is_time_in_range(now: datetime, hours_str: str) -> bool:
    """Check if the current time falls within a time range.

    Args:
        now: Current datetime (timezone-aware).
        hours_str: Time range string like "08:00-18:00".

    Returns:
        True if current time is within the range.
    """
    match = re.match(r"(\d{2}:\d{2})-(\d{2}:\d{2})", hours_str)
    if not match:
        logger.warning("Invalid hours format: %s", hours_str)
        return True

    start_str, end_str = match.groups()
    current_time = now.time()

    start_parts = start_str.split(":")
    end_parts = end_str.split(":")

    from datetime import time as dt_time

    start_time = dt_time(int(start_parts[0]), int(start_parts[1]))
    end_time = dt_time(int(end_parts[0]), int(end_parts[1]))

    return start_time <= current_time <= end_time
