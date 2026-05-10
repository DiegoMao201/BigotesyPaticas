"""Audit logging — append-only a un worksheet `Audit_Log` del spreadsheet.

Diseño:
- 100% opt-in (controlado por `bp_common.flags.AUDIT_LOG_ENABLED`).
- No bloqueante: si falla escribir el log, NUNCA debe romper la operación principal.
  Log a stderr como fallback.
- Crea la tab `Audit_Log` automáticamente si no existe.
- Esquema fijo: timestamp_co | actor | action | entity | entity_id | summary | payload_json
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any, Mapping

from bp_common.flags import get_flag
from bp_common.tz import now_co

_LOGGER = logging.getLogger("bp_common.audit")
if not _LOGGER.handlers:
    _h = logging.StreamHandler(sys.stderr)
    _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    _LOGGER.addHandler(_h)
    _LOGGER.setLevel(logging.INFO)

AUDIT_TAB = "Audit_Log"
AUDIT_HEADERS = [
    "timestamp_co",
    "actor",
    "action",
    "entity",
    "entity_id",
    "summary",
    "payload_json",
]


def _ensure_audit_tab(sh: Any):
    """Devuelve el worksheet `Audit_Log`, creándolo si hace falta."""
    try:
        ws = sh.worksheet(AUDIT_TAB)
    except Exception:
        ws = sh.add_worksheet(title=AUDIT_TAB, rows=1000, cols=len(AUDIT_HEADERS))
        ws.append_row(AUDIT_HEADERS, value_input_option="USER_ENTERED")
        return ws
    # Asegurar headers
    try:
        first = ws.row_values(1)
        if [h.strip() for h in first] != AUDIT_HEADERS:
            ws.update("A1", [AUDIT_HEADERS])
    except Exception:
        pass
    return ws


def log_event(
    sh: Any,
    *,
    action: str,
    entity: str,
    entity_id: str = "",
    summary: str = "",
    payload: Mapping[str, Any] | None = None,
    actor: str = "streamlit",
) -> bool:
    """Escribe una entrada al audit log. Devuelve True si se escribió, False si se saltó/falló.

    NUNCA lanza excepciones — los errores se loguean a stderr.
    """
    if not get_flag("AUDIT_LOG_ENABLED"):
        return False
    try:
        ws = _ensure_audit_tab(sh)
        row = [
            now_co().strftime("%Y-%m-%d %H:%M:%S"),
            actor,
            action,
            entity,
            str(entity_id),
            summary,
            json.dumps(payload or {}, ensure_ascii=False, default=str),
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("audit_log_failed: %s | action=%s entity=%s", exc, action, entity)
        return False
