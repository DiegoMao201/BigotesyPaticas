"""Timezone helpers — Colombia (America/Bogota)."""
from __future__ import annotations

from datetime import datetime

try:
    from zoneinfo import ZoneInfo  # py>=3.9
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]

try:
    import pytz  # type: ignore
except ImportError:  # pragma: no cover
    pytz = None  # type: ignore[assignment]


def get_bogota_timezone():
    """Devuelve un objeto tzinfo para `America/Bogota`. Prefiere `zoneinfo`."""
    if ZoneInfo is not None:
        return ZoneInfo("America/Bogota")
    if pytz is not None:
        return pytz.timezone("America/Bogota")
    raise RuntimeError("No hay soporte de zona horaria para America/Bogota.")


TZ_CO = get_bogota_timezone()


def now_co() -> datetime:
    """Datetime tz-aware en zona horaria de Colombia."""
    return datetime.now(TZ_CO)
