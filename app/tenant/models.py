"""Pydantic models for tenant configuration (settings.yaml).

These models define the complete schema that each tenant's settings.yaml
must conform to. The schema is validated at load time — invalid configs
fail fast with clear error messages.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Agent identity and behavior settings.

    Attributes:
        name: Display name of the agent.
        personality: Description of the agent's communication style.
        language: Language code for responses (e.g. pt-BR).
        system_prompt: Full system prompt template sent to the AI provider.
    """

    name: str
    personality: str = "Profissional e simpático"
    language: str = "pt-BR"
    system_prompt: str


class TopicsConfig(BaseModel):
    """Topic filtering rules.

    Attributes:
        allowed: Topics the agent is permitted to discuss.
        blocked: Topics the agent must refuse to discuss.
    """

    allowed: list[str] = Field(default_factory=list)
    blocked: list[str] = Field(default_factory=list)


class BusinessHoursSchedule(BaseModel):
    """Weekly business hours schedule.

    Each field accepts a time range string like ``08:00-18:00``
    or ``null`` for days without service.

    Attributes:
        monday_friday: Hours for weekdays.
        saturday: Hours for Saturday.
        sunday: Hours for Sunday.
    """

    monday_friday: str | None = None
    saturday: str | None = None
    sunday: str | None = None


class BusinessHoursConfig(BaseModel):
    """Business hours configuration.

    Attributes:
        timezone: IANA timezone name (e.g. America/Sao_Paulo).
        schedule: Weekly schedule definition.
        out_of_hours_message: Message returned outside business hours.
    """

    timezone: str = "America/Sao_Paulo"
    schedule: BusinessHoursSchedule = Field(default_factory=BusinessHoursSchedule)
    out_of_hours_message: str = "Estamos fora do horário de atendimento."


class EscalationConfig(BaseModel):
    """Escalation rules for handoff to a human agent.

    Attributes:
        trigger_keywords: Phrases that trigger escalation.
        action: What to do on escalation (``webhook`` or ``message``).
        webhook_url: URL to POST escalation events to.
        message: Message displayed to the user during escalation.
    """

    trigger_keywords: list[str] = Field(default_factory=list)
    action: str = "webhook"
    webhook_url: str | None = None
    message: str = "Vou te conectar com nossa equipe. Aguarde!"


class CacheConfig(BaseModel):
    """Semantic cache tuning parameters.

    Attributes:
        semantic_threshold: Minimum cosine similarity for a cache hit (0.0–1.0).
        ttl_hours: Time-to-live for cached responses in hours.
    """

    semantic_threshold: float = Field(default=0.92, ge=0.0, le=1.0)
    ttl_hours: int = Field(default=24, ge=1)


class WebhooksConfig(BaseModel):
    """Outbound webhook configuration.

    Attributes:
        events: List of event names to dispatch.
        endpoint: Target URL for webhook delivery.
        secret: Shared secret for HMAC signature (can reference env var).
    """

    events: list[str] = Field(default_factory=list)
    endpoint: str | None = None
    secret: str = ""


class TenantSettings(BaseModel):
    """Root schema for a tenant's settings.yaml.

    This is the full configuration for a single B2B client.
    All fields have sensible defaults except ``agent`` which
    requires at minimum a ``name`` and ``system_prompt``.

    Attributes:
        agent: Agent identity and personality.
        topics: Allowed and blocked conversation topics.
        business_hours: Operating schedule and out-of-hours message.
        escalation: Human handoff rules.
        cache: Semantic cache tuning.
        webhooks: Outbound event webhook settings.
    """

    agent: AgentConfig
    topics: TopicsConfig = Field(default_factory=TopicsConfig)
    business_hours: BusinessHoursConfig = Field(default_factory=BusinessHoursConfig)
    escalation: EscalationConfig = Field(default_factory=EscalationConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    webhooks: WebhooksConfig = Field(default_factory=WebhooksConfig)
