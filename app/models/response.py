"""Pydantic models for the agent's response."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ResponseSource(str, Enum):
    """Indicates where the response originated."""

    CACHE = "cache"
    AI = "ai"
    SYSTEM = "system"


class AgentResponse(BaseModel):
    """Response produced by the agent after processing a user message.

    Attributes:
        content: The text response to send back to the user.
        source: Whether the response came from cache, AI, or a system rule.
        cached: True if the response was served from semantic cache.
        latency_ms: Processing time in milliseconds.
        tokens_used: Number of tokens consumed (0 for cached responses).
    """

    content: str
    source: ResponseSource
    cached: bool = False
    latency_ms: float = 0.0
    tokens_used: int = 0
