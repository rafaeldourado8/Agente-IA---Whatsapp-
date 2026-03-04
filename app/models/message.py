"""Pydantic models for conversation messages."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of the message author in the conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    """Type of message content."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"


class Message(BaseModel):
    """A single message in a conversation.

    Attributes:
        role: Who authored the message.
        content: Text body of the message.
        message_type: Type of content (text, image, audio).
        media_url: URL to media file if applicable.
        timestamp: When the message was created (UTC).
        metadata: Optional key-value pairs for extensibility.
    """

    role: MessageRole
    content: str
    message_type: MessageType = MessageType.TEXT
    media_url: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, str] = Field(default_factory=dict)
