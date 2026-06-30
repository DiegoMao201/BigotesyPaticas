"""Logging estructurado JSON.

Uso:
    from bp_common.logging_setup import setup_logging, get_logger
    setup_logging()
    log = get_logger(__name__)
    log.info("venta_registrada", extra={"id_venta": "V-123", "total": 12500})

Salida (stderr):
    {"ts":"2026-05-10T14:22:01-05:00","level":"INFO","logger":"app","msg":"venta_registrada",
     "id_venta":"V-123","total":12500,"git_sha":"e99f6dd","env":"prod"}
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

from bp_common.tz import TZ_CO
from bp_common.version_info import get_git_sha

_RESERVED = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=TZ_CO).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "git_sha": get_git_sha(),
            "env": os.getenv("APP_ENV", "local"),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for k, v in record.__dict__.items():
            if k not in _RESERVED and not k.startswith("_"):
                try:
                    json.dumps(v, default=str)
                    payload[k] = v
                except Exception:
                    payload[k] = repr(v)
        return json.dumps(payload, ensure_ascii=False, default=str)


_CONFIGURED = False


def setup_logging(level: str | int | None = None) -> None:
    """Configura el root logger con el formatter JSON. Idempotente."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    lvl = level or os.getenv("LOG_LEVEL", "INFO")
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(lvl)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
