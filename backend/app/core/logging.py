"""Structured JSON logging with request-id correlation.

Designed to be replaceable with structlog/OpenTelemetry exporters later;
never logs document contents or secrets.
"""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
from typing import Any

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        for key in ("endpoint", "method", "status_code", "latency_ms", "company_id",
                    "document_id", "job_id", "user_id", "error", "processing_status"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)[:2000]
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    for noisy in ("uvicorn.access", "httpx", "openai", "pdfminer"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str = "app") -> logging.Logger:
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Small helper so services can log structured metadata: log.info("msg", company_id=...)."""

    def process(self, msg: str, kwargs: dict) -> tuple:  # type: ignore[override]
        extra = kwargs.pop("extra", {})
        return msg, {"extra": {**self.extra, **extra}}
