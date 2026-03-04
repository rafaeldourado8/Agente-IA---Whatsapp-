"""Domain exception hierarchy.

Every exception that represents a business-rule or infrastructure
failure has its own class here. This ensures:
  - Callers can catch only the errors they know how to handle.
  - API error handlers can translate domain errors to HTTP responses.
  - No generic ``except Exception`` is needed in application code.
"""


class AgentException(Exception):
    """Base class for all domain exceptions."""

    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(self.message)


# --- Tenant errors ---

class TenantNotFoundError(AgentException):
    """Raised when a tenant ID has no corresponding configuration."""


class InvalidTenantConfigError(AgentException):
    """Raised when a tenant configuration file fails validation."""


# --- AI provider errors ---

class AIProviderError(AgentException):
    """Raised when the AI provider fails to generate a response."""


# --- Cache errors ---

class CacheOperationError(AgentException):
    """Raised when a cache read or write operation fails."""


# --- WhatsApp delivery errors ---

class WhatsAppDeliveryError(AgentException):
    """Raised when a WhatsApp message cannot be delivered."""


# --- Webhook errors ---

class WebhookDispatchError(AgentException):
    """Raised when a webhook event cannot be dispatched."""
