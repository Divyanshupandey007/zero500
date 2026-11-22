"""Structured JSON logging for the Zero500 backend.

Configures the root logger to emit one JSON object per log line so the
investigation pipeline is observable in production without an external APM
tool. Each investigation request logs: incident id, retrieval latency, LLM
latency, retrieved doc ids, and final confidence score.

A correlation id (``X-Request-ID`` request header, or a generated uuid) is
stored in a context variable and attached to every log line emitted during
that request, giving basic request tracing across the retrieval + LLM steps.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
from typing import Any

# Context variable holding the correlation id for the current request.
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


def get_correlation_id() -> str:
    return correlation_id_var.get()


def set_correlation_id(value: str) -> None:
    correlation_id_var.set(value)


class CorrelationIdFilter(logging.Filter):
    """Injects the current correlation id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


class JsonFormatter(logging.Formatter):
    """Formats log records as a single JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", ""),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Carry investigation-specific fields when present on the record.
        for field in (
            "incident_id",
            "retrieval_latency",
            "llm_latency",
            "retrieved_doc_ids",
            "confidence_score",
        ):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        return json.dumps(payload)


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(CorrelationIdFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Silence noisy third-party loggers below WARNING.
    for name in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
