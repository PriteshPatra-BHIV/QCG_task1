"""
logger.py - Structured logger for the QCG project.
Emits JSON lines (production) or human-readable text (development).

All caller-supplied context is passed as a single 'ctx' dict to avoid
collisions with Python's reserved LogRecord attribute names.

Log output
----------
- Always: stdout StreamHandler
- If QCG_LOG_FILE is set: RotatingFileHandler (10 MB, 5 backups)
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
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
        formatter = _JsonFormatter() if config.LOG_FORMAT == "json" else logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        )

        # stdout handler
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(level)
        sh.setFormatter(formatter)
        logger.addHandler(sh)

        # optional file handler
        log_file = os.environ.get("QCG_LOG_FILE", "")
        if log_file:
            os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
            fh = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
            )
            fh.setLevel(level)
            fh.setFormatter(formatter)
            logger.addHandler(fh)

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
