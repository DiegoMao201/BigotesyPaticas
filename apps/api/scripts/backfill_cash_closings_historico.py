#!/usr/bin/env python3
"""Backfill de cierres de caja históricos — genera cierres 'sin_conteo' para
fechas con ventas que nunca tuvieron un cierre de caja registrado.

Estos días NO se cuadran retroactivamente: nadie contó el efectivo en su
momento, así que saldo_contado y diferencia quedan NULL (nunca 0 — un cuadre
en 0 sería un dato inventado). El snapshot de ventas/créditos por método sí
se guarda porque ese dato es real (viene de sales.payments/sales.orders).
saldo_inicial y base_caja quedan en 0 en estos históricos, para no fingir
un fondo fijo que no existía en ese momento.

Idempotente: solo crea cierres para fechas que hoy NO tienen ninguna fila en
finance.cash_closings. Nunca toca un cierre existente (sin importar su
status). Correr dos veces seguidas no duplica ni modifica nada.

FECHA DE CORTE (--hasta, default = AYER en America/Bogota): finance.cash_closings
tiene UNIQUE(fecha). Sin corte, el script podría tragarse hoy o una fecha
futura si ya tienen ventas (ej. una venta de prueba) pero aún no tienen cierre
—dejando esa fecha ocupada por un 'sin_conteo' con base_caja=0, y ya no se
podría abrir un cierre real ese día. El corte excluye siempre hoy y el futuro.

Uso:
  python scripts/backfill_cash_closings_historico.py --dry-run
  python scripts/backfill_cash_closings_historico.py
  python scripts/backfill_cash_closings_historico.py --hasta 2026-08-01 --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.api.v1.finance import _compute_live_totals_bulk
from app.db import AsyncSessionLocal
from app.models.finance import CashClosing
from sqlalchemy import select, text

_TZINFO = ZoneInfo("America/Bogota")


def _ayer_bogota() -> date:
    return datetime.now(_TZINFO).date() - timedelta(days=1)


async def _fechas_a_backfillear(db, hasta: date) -> list[date]:
    rows = (
        await db.execute(
            text("""
            WITH fechas_con_ventas AS (
                SELECT DISTINCT DATE(occurred_at AT TIME ZONE 'America/Bogota') AS fecha
                FROM sales.orders
                WHERE status NOT IN ('cancelled')
            )
            SELECT fecha FROM fechas_con_ventas
            WHERE fecha NOT IN (SELECT fecha FROM finance.cash_closings)
              AND fecha < :hasta
            ORDER BY fecha
        """),
            {"hasta": hasta},
        )
    ).all()
    return [r.fecha for r in rows]


async def run(dry_run: bool, hasta: date | None) -> None:
    hasta = hasta or _ayer_bogota()
    print(f"Fecha de corte (--hasta): {hasta} (excluye hoy y el futuro)")

    async with AsyncSessionLocal() as db:
        fechas = await _fechas_a_backfillear(db, hasta)

        if not fechas:
            print(
                "Nada que backfillear — todas las fechas con ventas hasta el corte ya tienen cierre."
            )
            return

        print(f"Fechas con ventas sin cierre (< {hasta}): {len(fechas)}")
        print(f"  Rango: {fechas[0]} → {fechas[-1]}")

        if dry_run:
            print("\n--dry-run: no se escribe nada. Primeras y últimas 5 fechas afectadas:")
            muestra = fechas[:5] + (["..."] if len(fechas) > 10 else []) + fechas[-5:]
            for f in muestra:
                print(f"  {f}")
            return

        # Re-verificar inmediatamente antes de escribir (por si algo cambió
        # entre el dry-run y la corrida real) y calcular snapshots en una
        # sola pasada bulk, no 182 queries individuales.
        fechas = await _fechas_a_backfillear(db, hasta)
        if not fechas:
            print("Nada que backfillear (ya no quedan fechas pendientes).")
            return

        live_bulk = await _compute_live_totals_bulk(db, fechas[0], fechas[-1])

        creados = 0
        for fecha in fechas:
            # Idempotencia dura: re-chequear que nadie creó el cierre entre
            # el cálculo del bulk y este punto (ej. corrida concurrente).
            existe = (
                await db.execute(select(CashClosing.id).where(CashClosing.fecha == fecha))
            ).scalar_one_or_none()
            if existe is not None:
                continue

            live = live_bulk.get(
                fecha, {"ventas_por_metodo": {}, "creditos_por_metodo": {}, "total_ventas": 0.0}
            )
            db.add(
                CashClosing(
                    fecha=fecha,
                    status="sin_conteo",
                    saldo_inicial=Decimal("0"),
                    base_caja=Decimal("0"),
                    gastos_efectivo=Decimal("0"),
                    consignaciones=Decimal("0"),
                    snap_ventas_por_metodo=live["ventas_por_metodo"],
                    snap_creditos_por_metodo=live["creditos_por_metodo"],
                    snap_total_ventas=Decimal(str(live["total_ventas"])),
                    saldo_final_efectivo=None,
                    saldo_contado=None,
                    diferencia=None,
                    notas="Backfill histórico — nadie contó el efectivo este día.",
                    created_by="backfill_script",
                )
            )
            creados += 1

        await db.commit()
        print(f"\n✅ {creados} cierres 'sin_conteo' creados.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Solo muestra cuántas fechas afectaría"
    )
    parser.add_argument(
        "--hasta",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help="Backfillea solo fechas ANTERIORES a esta (default: ayer en America/Bogota). "
        "Nunca incluye hoy ni el futuro — cash_closings.fecha es UNIQUE.",
    )
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run, hasta=args.hasta))


if __name__ == "__main__":
    sys.exit(main() or 0)
