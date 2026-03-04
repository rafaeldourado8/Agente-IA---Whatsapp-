"""Structured logging configuration.

Provides a JSON formatter for production logs and context-rich
log records with tenant_id, session_id, and performance metrics.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects.

    Produces structured logs suitable for log aggregation tools
    (e.g. ELK, Datadog, CloudWatch). Includes extra context
    fields when present (tenant_id, session_id, latency, etc.).
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON.

        Args:
            record: The log record to format.

        Returns:
            JSON string with structured log data.
        """
        log_entry: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include context fields if present
        for field in (
            "tenant_id",
            "session_id",
            "latency_ms",
            "cache_hit",
            "source",
            "phone",
            "event",
        ):
            value = getattr(record, field, None)
            if value is not None:
                log_entry[field] = value

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class ContextLogger:
    """Logger wrapper that automatically includes context fields.

    Use this in request handlers to log with tenant_id and
    session_id attached to every record.

    Example::

        log = ContextLogger("app.agent", tenant_id="acme", session_id="s1")
        log.info("Processing message", latency_ms=123.4, cache_hit=True)
    """

    def __init__(
        self,
        name: str,
        tenant_id: str = "",
        session_id: str = "",
    ) -> None:
        self._logger = logging.getLogger(name)
        self._context = {
            "tenant_id": tenant_id,
            "session_id": session_id,
        }

    def _log(
        self,
        level: int,
        msg: str,
        **kwargs: Any,
    ) -> None:
        """Log with context fields merged into extra."""
        extra = {**self._context, **kwargs}
        self._logger.log(level, msg, extra=extra)

    def debug(self, msg: str, **kwargs: Any) -> None:
        """Log at DEBUG level."""
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        """Log at INFO level."""
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log at WARNING level."""
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        """Log at ERROR level."""
        self._log(logging.ERROR, msg, **kwargs)


def configure_logging(level: str = "INFO", json_format: bool = True) -> None:
    """Configure the root logger with structured formatting.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR).
        json_format: If True, use JSON formatter. Otherwise, plain text.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        ))

    root.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
