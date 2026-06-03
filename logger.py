"""
logger.py - Structured logger for the QCG project.
Emits JSON lines (production) or human-readable text (development).

All caller-supplied context is passed as a single 'ctx' dict to avoid
collisions with Python's reserved LogRecord attribute names.
"""

from __future__ import annotations

import json
import logging
import sys
import threading
from datetime import datetime, timezone

import config

_logger_lock = threading.Lock()


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        ctx = getattr(record, "ctx", None)
        if ctx:
            payload["ctx"] = ctx
        return json.dumps(payload)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    with _logger_lock:
        if logger.handlers:
            return logger

        level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        if config.LOG_FORMAT == "json":
            handler.setFormatter(_JsonFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
            ))

        logger.addHandler(handler)
        logger.propagate = False
    return logger


def log_event(logger: logging.Logger, level: int, event: str, ctx: dict = None):
    """
    Emit a structured log entry. All context goes into 'ctx' to avoid
    collisions with reserved LogRecord keys (message, asctime, etc.).
    """
    record = logger.makeRecord(
        logger.name, level, "(unknown)", 0, event, (), None
    )
    if ctx:
        record.ctx = ctx
    logger.handle(record)
