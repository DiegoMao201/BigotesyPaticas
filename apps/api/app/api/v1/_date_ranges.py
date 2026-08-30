"""Helpers de rango de fechas para endpoints de analítica.

Todos los límites de día/mes se calculan en America/Bogota (zona horaria del
negocio, sin DST) y se convierten a UTC antes de compararse contra columnas
TIMESTAMPTZ — mismo patrón ya usado en finance.py (_TZ/_TZINFO,
`occurred_at AT TIME ZONE 'America/Bogota'`). Calcular estos límites en UTC
crudo desalinea los KPIs "mes a la fecha" con lo que el negocio considera
"hoy"/"este mes" en Bogotá.
"""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

_TZ = "America/Bogota"
_TZINFO = ZoneInfo(_TZ)

MAX_RANGE_DAYS = 730


def now_bogota() -> datetime:
    return datetime.now(_TZINFO)


def _bogota_midnight(d: date) -> datetime:
    """Medianoche de `d` en America/Bogota, como datetime aware."""
    return datetime(d.year, d.month, d.day, tzinfo=_TZINFO)


def resolve_window(
    days: int | None,
    start_date: date | None,
    end_date: date | None,
    default_days: int,
) -> tuple[datetime, datetime]:
    """Devuelve (since, until) en UTC, listos para comparar contra columnas
    TIMESTAMPTZ.

    Si vienen `start_date`/`end_date`, se resuelven como límites de día
    completo en America/Bogota (00:00 del día `start` hasta 00:00 del día
    siguiente a `end`) y se convierten a UTC. Si no, se usa una ventana móvil
    de `days` días hacia atrás desde ahora (comportamiento previo del
    endpoint, sin cambios).

    Si `start_date > end_date` se intercambian. El span se recorta a
    `MAX_RANGE_DAYS` para evitar escaneos completos de sales.orders con
    rangos absurdos (ej. 10 años).
    """
    now_utc = datetime.now(UTC)

    if start_date or end_date:
        end = end_date or now_bogota().date()
        start = start_date or (end - timedelta(days=default_days - 1))

        if start > end:
            start, end = end, start

        if (end - start).days > MAX_RANGE_DAYS:
            start = end - timedelta(days=MAX_RANGE_DAYS)

        since = _bogota_midnight(start).astimezone(UTC)
        until = _bogota_midnight(end + timedelta(days=1)).astimezone(UTC)
        until = min(until, now_utc)
        return since, until

    until = now_utc
    since = now_utc - timedelta(days=days or default_days)
    return since, until


def previous_window(since: datetime, until: datetime) -> tuple[datetime, datetime]:
    """Rango inmediatamente anterior, de la MISMA duración."""
    span = until - since
    return since - span, since


def mtd_ranges(
    now_utc: datetime | None = None,
) -> tuple[datetime, datetime, datetime, datetime]:
    """MTD-vs-MTD real, calculado en America/Bogota.

    Devuelve (start_this_month, now, start_prev_month, end_prev_month_cutoff)
    — todos en UTC, listos para usarse directo en queries.

    `end_prev_month_cutoff` es el fin del mismo día-del-mes que hoy, pero del
    mes anterior (recortado con `calendar.monthrange` si ese mes tiene menos
    días, ej. hoy 31 y el mes anterior tiene 28/29/30).
    """
    now_utc = now_utc or datetime.now(UTC)
    now_bog = now_utc.astimezone(_TZINFO)

    start_month_bog = now_bog.replace(hour=0, minute=0, second=0, microsecond=0, day=1)
    day_n = now_bog.day

    if start_month_bog.month == 1:
        prev_year, prev_month = start_month_bog.year - 1, 12
    else:
        prev_year, prev_month = start_month_bog.year, start_month_bog.month - 1

    prev_days_in_month = calendar.monthrange(prev_year, prev_month)[1]
    cutoff_day = min(day_n, prev_days_in_month)

    start_prev_bog = datetime(prev_year, prev_month, 1, tzinfo=_TZINFO)
    end_prev_bog = datetime(prev_year, prev_month, cutoff_day, tzinfo=_TZINFO) + timedelta(days=1)

    return (
        start_month_bog.astimezone(UTC),
        now_utc,
        start_prev_bog.astimezone(UTC),
        end_prev_bog.astimezone(UTC),
    )
