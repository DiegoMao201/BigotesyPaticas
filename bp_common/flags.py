"""Feature flags — capa simple basada en variables de entorno + override en runtime.

Diseño:
- Defaults seguros (todo desactivado salvo `DUAL_WRITE_SHEETS=true`).
- Cualquier flag se puede sobreescribir en tiempo de ejecución vía
  `set_flag(name, bool)` (útil para tests o para un panel admin futuro).
- Nombres canónicos: `FF_*` (forward-compat con la API y workers).

La app Streamlit puede consultar:
    from bp_common.flags import get_flag
    if get_flag("USE_PG_CATALOG_READ"):
        ...
"""
from __future__ import annotations

import os
from typing import Dict

_DEFAULTS: Dict[str, bool] = {
    "USE_PG_CATALOG_READ": False,
    "USE_PG_CATALOG_WRITE": False,
    "USE_PG_POS": False,
    "DUAL_WRITE_SHEETS": True,
    "AUDIT_LOG_ENABLED": True,
    "BACKUP_ENABLED": True,
}

_OVERRIDES: Dict[str, bool] = {}


def _parse_bool(raw: str | None) -> bool | None:
    if raw is None:
        return None
    s = raw.strip().lower()
    if s in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "f", "no", "n", "off", ""}:
        return False
    return None


def get_flag(name: str) -> bool:
    """Obtiene un flag en este orden: override runtime → env (`FF_<name>`) → default."""
    name = name.upper()
    if name in _OVERRIDES:
        return _OVERRIDES[name]
    env_val = _parse_bool(os.getenv(f"FF_{name}"))
    if env_val is not None:
        return env_val
    return _DEFAULTS.get(name, False)


def set_flag(name: str, value: bool) -> None:
    """Override en runtime (no persiste)."""
    _OVERRIDES[name.upper()] = bool(value)


def reset_overrides() -> None:
    _OVERRIDES.clear()


def all_flags() -> Dict[str, bool]:
    """Snapshot completo de flags actuales (útil para mostrar en sidebar)."""
    return {name: get_flag(name) for name in _DEFAULTS}
