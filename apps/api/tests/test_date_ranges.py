"""Tests de _date_ranges.py — todos los límites deben calcularse en
America/Bogota (UTC-5, sin DST), no en UTC crudo."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.api.v1._date_ranges import (
    MAX_RANGE_DAYS,
    mtd_ranges,
    previous_window,
    resolve_window,
)

_BOG = ZoneInfo("America/Bogota")


def _bog(y, m, d, h=0, mi=0) -> datetime:
    return datetime(y, m, d, h, mi, tzinfo=_BOG)


# ─── mtd_ranges ─────────────────────────────────────────────────────────


def test_mtd_dia_31_vs_febrero_no_bisiesto() -> None:
    # Hoy: 31 de marzo de 2026 (2026 no es bisiesto → febrero tiene 28 días)
    now = _bog(2026, 3, 31, 12, 0).astimezone(UTC)
    start_month, until, start_prev, end_prev = mtd_ranges(now)

    assert start_month == _bog(2026, 3, 1).astimezone(UTC)
    assert until == now
    assert start_prev == _bog(2026, 2, 1).astimezone(UTC)
    # Cutoff recortado a 28 (no existe 31 de febrero) → fin = 1 de marzo
    assert end_prev == _bog(2026, 3, 1).astimezone(UTC)


def test_mtd_29_febrero_bisiesto_como_hoy() -> None:
    # 2028 es bisiesto → 29 de febrero existe
    now = _bog(2028, 2, 29, 9, 0).astimezone(UTC)
    start_month, _until, start_prev, end_prev = mtd_ranges(now)

    assert start_month == _bog(2028, 2, 1).astimezone(UTC)
    assert start_prev == _bog(2028, 1, 1).astimezone(UTC)
    # Enero tiene 31 días, cutoff = min(29, 31) = 29 → fin = 30 de enero
    assert end_prev == _bog(2028, 1, 30).astimezone(UTC)


def test_mtd_29_febrero_como_referencia_mes_anterior_no_bisiesto() -> None:
    # Hoy: 29 de marzo de 2026 (no bisiesto) → febrero anterior solo tiene 28 días
    now = _bog(2026, 3, 29, 8, 0).astimezone(UTC)
    _start_month, _until, _start_prev, end_prev = mtd_ranges(now)

    # cutoff = min(29, 28) = 28 → fin = 1 de marzo (no explota con "29 feb" inexistente)
    assert end_prev == _bog(2026, 3, 1).astimezone(UTC)


def test_mtd_cambio_de_anio() -> None:
    # Hoy: 15 de enero de 2026 → mes anterior es diciembre de 2025
    now = _bog(2026, 1, 15, 10, 0).astimezone(UTC)
    start_month, _until, start_prev, end_prev = mtd_ranges(now)

    assert start_month == _bog(2026, 1, 1).astimezone(UTC)
    assert start_prev == _bog(2025, 12, 1).astimezone(UTC)
    assert end_prev == _bog(2025, 12, 16).astimezone(UTC)


def test_mtd_dia_1_del_mes() -> None:
    # Hoy: 1 de junio de 2026, a cualquier hora del día
    now = _bog(2026, 6, 1, 23, 45).astimezone(UTC)
    start_month, until, start_prev, end_prev = mtd_ranges(now)

    assert start_month == _bog(2026, 6, 1).astimezone(UTC)
    assert until == now
    assert start_prev == _bog(2026, 5, 1).astimezone(UTC)
    # cutoff = min(1, 31) = 1 → fin = 2 de mayo
    assert end_prev == _bog(2026, 5, 2).astimezone(UTC)


def test_mtd_cruce_medianoche_bogota_utc() -> None:
    """El bug real: 02:00 UTC del 1-ago = 21:00 del 31-jul en Bogotá.

    Con UTC crudo, `now.replace(day=1)` cree que ya es agosto. En Bogotá
    todavía es julio — start_month debe caer en julio, no en agosto.
    """
    now_utc = datetime(2026, 8, 1, 2, 0, tzinfo=UTC)  # 31-jul 21:00 Bogotá
    start_month, until, start_prev, _end_prev = mtd_ranges(now_utc)

    assert start_month == _bog(2026, 7, 1).astimezone(UTC)
    assert start_month != _bog(2026, 8, 1).astimezone(UTC)
    assert start_prev == _bog(2026, 6, 1).astimezone(UTC)
    assert until == now_utc


# ─── resolve_window ─────────────────────────────────────────────────────


def test_resolve_window_sin_fechas_usa_days() -> None:
    now = datetime.now(UTC)
    since, until = resolve_window(days=45, start_date=None, end_date=None, default_days=90)
    assert (until - since) == timedelta(days=45)
    assert abs((until - now).total_seconds()) < 5


def test_resolve_window_con_fechas_limites_bogota() -> None:
    since, until = resolve_window(
        days=None, start_date=date(2026, 6, 10), end_date=date(2026, 6, 12), default_days=90
    )
    assert since == _bog(2026, 6, 10).astimezone(UTC)
    assert until == _bog(2026, 6, 13).astimezone(UTC)  # fin de 12-jun = medianoche 13-jun


def test_resolve_window_start_mayor_que_end_se_invierte() -> None:
    since, until = resolve_window(
        days=None, start_date=date(2026, 6, 20), end_date=date(2026, 6, 15), default_days=90
    )
    assert since < until
    assert since == _bog(2026, 6, 15).astimezone(UTC)


def test_resolve_window_recorta_a_max_range_days() -> None:
    since, until = resolve_window(
        days=None, start_date=date(2000, 1, 1), end_date=date(2026, 1, 1), default_days=90
    )
    assert (until - since).days <= MAX_RANGE_DAYS + 1  # +1 por el "fin de día" del end


def test_resolve_window_until_no_supera_ahora() -> None:
    hoy_bog = datetime.now(_BOG).date()
    manana = hoy_bog + timedelta(days=1)
    since, until = resolve_window(days=None, start_date=hoy_bog, end_date=manana, default_days=90)
    assert until <= datetime.now(UTC)


# ─── previous_window ────────────────────────────────────────────────────


def test_previous_window_misma_duracion() -> None:
    since = _bog(2026, 6, 10).astimezone(UTC)
    until = _bog(2026, 6, 20).astimezone(UTC)
    prev_since, prev_until = previous_window(since, until)
    assert prev_until == since
    assert (until - since) == (prev_until - prev_since)
