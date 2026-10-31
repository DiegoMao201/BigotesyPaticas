"""Contabilidad: UNA sola forma de armar los estados financieros (30-oct-2026).

Diego: *"esto en el admin está mal calculado [...] información ya tenemos
suficiente para hacer una buena contabilidad y unos buenos estados
financieros"*.

Hasta hoy el estado de resultados se calculaba en tres sitios distintos
(`/analytics/bi`, `/finance/summary` y el Excel), cada uno con sus reglas, y
ninguna era contable:

- El gasto del día de hoy nunca entraba (`fecha < hoy`) mientras la venta de
  hoy sí: el P&L del 30-oct no mostraba la nómina pagada ese día.
- Un abono a un crédito ($580.000, "Pago credito") contaba como gasto. El
  capital de un préstamo no es gasto; sale de caja, no del resultado.
- Las inversiones (activos) y las compras de mercancía que se registraron como
  gasto hasta mayo se sumaban encima del costo de ventas: el mismo peso dos veces.
- La comisión del datáfono se mostraba en una tarjeta aparte pero no se restaba.
- Los pedidos del portal se facturaban con costo 0, así que su margen salía
  del 100 %.

Aquí viven las reglas, y los endpoints solo las llaman:

- **Ventas netas** = `grand_total` de ventas no anuladas (ya descontados los
  descuentos y el bono de bienvenida; el envío NO es venta, va aparte).
- **Costo de ventas** = costo unitario congelado en cada línea vendida. El costo
  incluye el IVA que se pagó al proveedor: la tienda no discrimina IVA en sus
  ventas, así que ese IVA es costo real.
- **Gastos operativos** = `finance.expenses` clasificados por `tipo`/`categoria`
  (ver `CLASE_GASTO_SQL`). Inventario, inversiones y abonos a crédito salen del
  resultado y se muestran aparte como "fuera del resultado".
- **Gastos financieros** = comisión estimada del datáfono sobre los pagos con
  tarjeta (misma tarifa que `finance.datafono-impact`).

Los rangos llegan en UTC (`_date_ranges.resolve_window`); los gastos se filtran
por fecha calendario de Bogotá, ambos extremos incluidos.
"""

from __future__ import annotations

import calendar
from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.config import get_settings

_TZ = ZoneInfo("America/Bogota")

VENTA_VALIDA = "o.status NOT IN ('cancelled', 'refunded')"

#: Qué es gasto del período y qué no. Las etiquetas históricas son variadas
#: (`Costo de Venta`, `Variable`, `Gasto Operativo`...), por eso se mira
#: categoría y tipo. Cualquier cosa que no sea inventario, inversión o crédito
#: es gasto operativo.
CLASE_GASTO_SQL = """
    CASE
        WHEN categoria IN ('Compra Inventario', 'Inventario')
             OR tipo IN ('Costo de Venta', 'Mercancía') THEN 'inventario'
        WHEN tipo = 'Inversión' THEN 'inversion'
        WHEN tipo = 'Abono a crédito' THEN 'credito'
        ELSE 'operativo'
    END
"""

CLASES = ("operativo", "inventario", "inversion", "credito")


def clasificar_gasto(categoria: str | None, tipo: str | None) -> str:
    """Misma regla que `CLASE_GASTO_SQL`, en Python, para poder probarla."""
    if (categoria or "") in ("Compra Inventario", "Inventario") or (tipo or "") in (
        "Costo de Venta",
        "Mercancía",
    ):
        return "inventario"
    if tipo == "Inversión":
        return "inversion"
    if tipo == "Abono a crédito":
        return "credito"
    return "operativo"


def fecha_bogota(dt: datetime) -> date:
    return dt.astimezone(_TZ).date()


def _rango_fechas(since: datetime, until: datetime) -> tuple[date, date]:
    """Fechas calendario (Bogotá) que cubre [since, until), ambas incluidas."""
    return fecha_bogota(since), fecha_bogota(until - timedelta(seconds=1))


def _pct(parte: float, total: float) -> float:
    return round(parte / total * 100, 1) if total else 0.0


def _f(v) -> float:
    return float(v or 0)


# ───────────────────────── Estado de resultados ─────────────────────────


async def _cifras_periodo(db, since: datetime, until: datetime) -> dict:
    """Las cifras crudas del período, directo de la base. Nada derivado aquí."""
    ventas = (
        (
            await db.execute(
                text(f"""
                    SELECT coalesce(sum(o.subtotal), 0)        AS ventas_brutas,
                           coalesce(sum(o.discount_total), 0)  AS descuentos,
                           coalesce(sum((o.metadata->'bono'->>'valor')::numeric), 0) AS bonos,
                           coalesce(sum(o.shipping_total), 0)  AS envios,
                           coalesce(sum(o.grand_total), 0)     AS ventas_netas,
                           count(*)                            AS n_ventas,
                           count(DISTINCT date(timezone('America/Bogota', o.occurred_at))) AS dias_con_venta
                    FROM sales.orders o
                    WHERE o.occurred_at >= :since AND o.occurred_at < :until AND {VENTA_VALIDA}
                """),
                {"since": since, "until": until},
            )
        )
        .mappings()
        .one()
    )
    items = (
        (
            await db.execute(
                text(f"""
                    SELECT coalesce(sum(i.unit_cost * i.quantity), 0) AS costo_ventas,
                           coalesce(sum(i.quantity), 0)               AS unidades,
                           coalesce(sum(i.quantity) FILTER (WHERE coalesce(i.unit_cost, 0) = 0), 0)
                               AS unidades_sin_costo,
                           count(*) FILTER (WHERE i.unit_cost > i.unit_price) AS lineas_bajo_costo,
                           coalesce(sum((i.unit_cost - i.unit_price) * i.quantity)
                               FILTER (WHERE i.unit_cost > i.unit_price), 0) AS perdida_bajo_costo
                    FROM sales.order_items i
                    JOIN sales.orders o ON o.id = i.order_id
                    WHERE o.occurred_at >= :since AND o.occurred_at < :until AND {VENTA_VALIDA}
                """),
                {"since": since, "until": until},
            )
        )
        .mappings()
        .one()
    )
    desde, hasta = _rango_fechas(since, until)
    gastos = (
        (
            await db.execute(
                text(f"""
                    SELECT {CLASE_GASTO_SQL} AS clase,
                           coalesce(nullif(categoria, ''), 'Sin categoría') AS categoria,
                           bool_or(coalesce(es_fijo, false)) AS es_fijo,
                           sum(monto) AS total,
                           count(*)   AS n
                    FROM finance.expenses
                    WHERE fecha >= :desde AND fecha <= :hasta
                    GROUP BY 1, 2
                    ORDER BY 4 DESC
                """),
                {"desde": desde, "hasta": hasta},
            )
        )
        .mappings()
        .all()
    )
    tarjeta = (
        (
            await db.execute(
                text(f"""
                    SELECT coalesce(sum(p.amount), 0) AS monto, count(*) AS n
                    FROM sales.payments p
                    JOIN sales.orders o ON o.id = p.order_id
                    WHERE p.method = 'Tarjeta'
                      AND o.occurred_at >= :since AND o.occurred_at < :until AND {VENTA_VALIDA}
                """),
                {"since": since, "until": until},
            )
        )
        .mappings()
        .one()
    )
    compras = (
        await db.execute(
            text("""
                SELECT coalesce(sum(total), 0) FROM purchasing.purchases
                WHERE status = 'received' AND purchased_at >= :since AND purchased_at < :until
            """),
            {"since": since, "until": until},
        )
    ).scalar_one()
    return {
        "ventas": dict(ventas),
        "items": dict(items),
        "gastos": [dict(g) for g in gastos],
        "tarjeta": dict(tarjeta),
        "compras_mercancia": _f(compras),
        "desde": desde,
        "hasta": hasta,
    }


def comision_tarjeta(monto: float, n: int) -> float:
    """Comisión estimada del datáfono: la misma tarifa de `finance.datafono-impact`."""
    s = get_settings()
    return round(monto * s.datafono_tasa_pct / 100 + n * s.datafono_fijo_por_txn, 2)


def armar_estado(c: Mapping) -> dict:
    """De las cifras crudas al estado de resultados. Función pura: se prueba sola."""
    v, it = c["ventas"], c["items"]
    ventas_netas = _f(v["ventas_netas"])
    costo = _f(it["costo_ventas"])
    utilidad_bruta = ventas_netas - costo

    por_clase: dict[str, float] = {k: 0.0 for k in CLASES}
    categorias: list[dict] = []
    fijos = variables = 0.0
    for g in c["gastos"]:
        clase = g["clase"]
        por_clase[clase] = por_clase.get(clase, 0.0) + _f(g["total"])
        if clase == "operativo":
            fila = {
                "categoria": g["categoria"],
                "total": _f(g["total"]),
                "es_fijo": bool(g["es_fijo"]),
                "n": int(g["n"]),
            }
            categorias.append(fila)
            if fila["es_fijo"]:
                fijos += fila["total"]
            else:
                variables += fila["total"]
    gastos_operativos = por_clase["operativo"]
    utilidad_operacional = utilidad_bruta - gastos_operativos

    comision = comision_tarjeta(_f(c["tarjeta"]["monto"]), int(c["tarjeta"]["n"]))
    utilidad_neta = utilidad_operacional - comision

    margen_bruto = _pct(utilidad_bruta, ventas_netas)
    # Punto de equilibrio del período: cuánto había que vender, con este margen,
    # para pagar los gastos del período. Cobertura = cuánto de eso se vendió.
    gastos_a_cubrir = gastos_operativos + comision
    equilibrio = gastos_a_cubrir / (margen_bruto / 100) if margen_bruto > 0 else 0.0

    return {
        "periodo": {
            "desde": c["desde"].isoformat(),
            "hasta": c["hasta"].isoformat(),
            "dias": (c["hasta"] - c["desde"]).days + 1,
            "dias_con_venta": int(v["dias_con_venta"] or 0),
        },
        "ventas_brutas": _f(v["ventas_brutas"]),
        "descuentos": _f(v["descuentos"]),
        "bonos_bienvenida": _f(v["bonos"]),
        "ventas_netas": ventas_netas,
        "n_ventas": int(v["n_ventas"] or 0),
        "unidades": int(it["unidades"] or 0),
        "ticket_promedio": round(ventas_netas / int(v["n_ventas"]), 0) if v["n_ventas"] else 0.0,
        "costo_ventas": costo,
        "utilidad_bruta": utilidad_bruta,
        "margen_bruto_pct": margen_bruto,
        "gastos_operativos": gastos_operativos,
        "gastos_fijos": fijos,
        "gastos_variables": variables,
        "gastos_por_categoria": categorias,
        "utilidad_operacional": utilidad_operacional,
        "margen_operacional_pct": _pct(utilidad_operacional, ventas_netas),
        "comision_tarjeta": comision,
        "ventas_tarjeta": _f(c["tarjeta"]["monto"]),
        "utilidad_neta": utilidad_neta,
        "margen_neto_pct": _pct(utilidad_neta, ventas_netas),
        "punto_equilibrio": round(equilibrio, 0),
        "cobertura_pct": _pct(ventas_netas, equilibrio) if equilibrio else 0.0,
        "fuera_del_resultado": {
            "compras_mercancia": c["compras_mercancia"],
            "compras_como_gasto": por_clase["inventario"],
            "inversiones": por_clase["inversion"],
            "abonos_credito": por_clase["credito"],
            "envios_cobrados": _f(v["envios"]),
        },
        "calidad": {
            "unidades_sin_costo": int(it["unidades_sin_costo"] or 0),
            "lineas_bajo_costo": int(it["lineas_bajo_costo"] or 0),
            "perdida_bajo_costo": _f(it["perdida_bajo_costo"]),
            "gastos_sin_clasificar": sum(
                _f(g["total"])
                for g in c["gastos"]
                if g["clase"] == "operativo" and g["categoria"] in ("Otros", "Sin categoría")
            ),
        },
    }


async def estado_resultados(db, since: datetime, until: datetime) -> dict:
    return armar_estado(await _cifras_periodo(db, since, until))


# ───────────────────────── Balance (a hoy) ─────────────────────────


async def balance(db) -> dict:
    """Lo que la tienda tiene y debe HOY. Inventario y saldos no tienen historia
    fiel en la base, así que el balance siempre es a la fecha de consulta."""
    s = get_settings()
    hoy = datetime.now(_TZ).date()
    desde_bold = hoy - timedelta(days=s.datafono_dias_deposito - 1)
    fila = (
        (
            await db.execute(
                text("""
                    SELECT
                      (SELECT coalesce(sum(st.quantity * coalesce(p.cost, 0)), 0)
                         FROM inventory.stock st JOIN catalog.products p ON p.id = st.product_id
                        WHERE st.quantity > 0) AS inventario_costo,
                      (SELECT coalesce(sum(st.quantity * coalesce(p.price, 0)), 0)
                         FROM inventory.stock st JOIN catalog.products p ON p.id = st.product_id
                        WHERE st.quantity > 0) AS inventario_venta,
                      (SELECT coalesce(sum(st.quantity), 0) FROM inventory.stock st WHERE st.quantity > 0)
                        AS inventario_unidades,
                      (SELECT count(*) FROM inventory.stock st JOIN catalog.products p ON p.id = st.product_id
                        WHERE st.quantity > 0 AND coalesce(p.cost, 0) = 0) AS productos_sin_costo,
                      (SELECT coalesce(sum(balance_due), 0) FROM sales.orders
                        WHERE status NOT IN ('cancelled', 'refunded') AND balance_due > 0) AS cuentas_por_cobrar,
                      (SELECT count(*) FROM sales.orders
                        WHERE status NOT IN ('cancelled', 'refunded') AND balance_due > 0) AS ventas_por_cobrar,
                      (SELECT coalesce(sum(total), 0) FROM purchasing.purchases
                        WHERE status = 'received' AND coalesce(payment_status, '') <> 'pagada') AS proveedores_por_pagar,
                      (SELECT count(*) FROM purchasing.purchases
                        WHERE status = 'received' AND coalesce(payment_status, '') <> 'pagada') AS facturas_por_pagar,
                      (SELECT coalesce(sum(total), 0) FROM purchasing.purchases
                        WHERE status = 'received' AND coalesce(payment_status, '') <> 'pagada'
                          AND due_date < :hoy) AS proveedores_vencido,
                      (SELECT coalesce(sum(total_provision), 0) FROM finance.payrolls
                        WHERE estado = 'pagada') AS prestaciones_provisionadas,
                      (SELECT coalesce(sum(p.amount), 0) FROM sales.payments p JOIN sales.orders o ON o.id = p.order_id
                        WHERE p.method = 'Tarjeta' AND o.status <> 'cancelled'
                          AND date(timezone('America/Bogota', o.occurred_at)) >= :desde_bold) AS tarjeta_reciente,
                      (SELECT count(*) FROM sales.payments p JOIN sales.orders o ON o.id = p.order_id
                        WHERE p.method = 'Tarjeta' AND o.status <> 'cancelled'
                          AND date(timezone('America/Bogota', o.occurred_at)) >= :desde_bold) AS tarjeta_reciente_n
                """),
                {"hoy": hoy, "desde_bold": desde_bold},
            )
        )
        .mappings()
        .one()
    )
    caja = (
        (
            await db.execute(
                text("""
                    SELECT fecha, coalesce(saldo_contado, saldo_final_efectivo) AS saldo
                    FROM finance.cash_closings
                    WHERE status = 'closed' AND coalesce(saldo_contado, saldo_final_efectivo) IS NOT NULL
                    ORDER BY fecha DESC LIMIT 1
                """)
            )
        )
        .mappings()
        .first()
    )
    bold_por_recibir = _f(fila["tarjeta_reciente"]) - comision_tarjeta(
        _f(fila["tarjeta_reciente"]), int(fila["tarjeta_reciente_n"])
    )
    activos = {
        "caja": _f(caja["saldo"]) if caja else None,
        "caja_fecha": caja["fecha"].isoformat() if caja else None,
        "bold_por_recibir": round(bold_por_recibir, 2),
        "cuentas_por_cobrar": _f(fila["cuentas_por_cobrar"]),
        "ventas_por_cobrar": int(fila["ventas_por_cobrar"]),
        "inventario_costo": _f(fila["inventario_costo"]),
        "inventario_venta": _f(fila["inventario_venta"]),
        "inventario_unidades": int(fila["inventario_unidades"]),
        "productos_sin_costo": int(fila["productos_sin_costo"]),
    }
    pasivos = {
        "proveedores_por_pagar": _f(fila["proveedores_por_pagar"]),
        "facturas_por_pagar": int(fila["facturas_por_pagar"]),
        "proveedores_vencido": _f(fila["proveedores_vencido"]),
        "prestaciones_provisionadas": _f(fila["prestaciones_provisionadas"]),
    }
    total_activos = (
        (activos["caja"] or 0)
        + activos["bold_por_recibir"]
        + activos["cuentas_por_cobrar"]
        + activos["inventario_costo"]
    )
    total_pasivos = pasivos["proveedores_por_pagar"] + pasivos["prestaciones_provisionadas"]
    return {
        "fecha": hoy.isoformat(),
        "activos": activos,
        "pasivos": pasivos,
        "total_activos": round(total_activos, 2),
        "total_pasivos": round(total_pasivos, 2),
        "capital_trabajo": round(total_activos - total_pasivos, 2),
    }


# ───────────────────────── Flujo de caja ─────────────────────────


async def flujo_caja(db, since: datetime, until: datetime) -> dict:
    """Plata que entró y salió en el período, por dónde entró y por dónde salió.
    Base de caja: cuenta cuando se cobra o se paga, no cuando se vende."""
    desde, hasta = _rango_fechas(since, until)
    entradas = (
        (
            await db.execute(
                text("""
                    SELECT initcap(coalesce(nullif(p.method, ''), 'Sin método')) AS metodo,
                           sum(p.amount) AS total, count(*) AS n
                    FROM sales.payments p JOIN sales.orders o ON o.id = p.order_id
                    WHERE p.received_at >= :since AND p.received_at < :until
                      AND o.status <> 'cancelled'
                    GROUP BY 1 ORDER BY 2 DESC
                """),
                {"since": since, "until": until},
            )
        )
        .mappings()
        .all()
    )
    proveedores = (
        (
            await db.execute(
                text("""
                    SELECT initcap(coalesce(nullif(payment_method, ''), 'Sin método')) AS metodo,
                           sum(total) AS total, count(*) AS n
                    FROM purchasing.purchases
                    WHERE status = 'received' AND payment_status = 'pagada'
                      AND coalesce(paid_at, purchased_at) >= :since
                      AND coalesce(paid_at, purchased_at) < :until
                    GROUP BY 1 ORDER BY 2 DESC
                """),
                {"since": since, "until": until},
            )
        )
        .mappings()
        .all()
    )
    gastos = (
        (
            await db.execute(
                text(f"""
                    SELECT {CLASE_GASTO_SQL} AS clase,
                           coalesce(nullif(metodo_pago, ''), 'Sin método') AS metodo,
                           sum(monto) AS total, count(*) AS n
                    FROM finance.expenses
                    WHERE fecha >= :desde AND fecha <= :hasta
                    GROUP BY 1, 2 ORDER BY 3 DESC
                """),
                {"desde": desde, "hasta": hasta},
            )
        )
        .mappings()
        .all()
    )
    ent = [{"metodo": r["metodo"], "total": _f(r["total"]), "n": int(r["n"])} for r in entradas]
    prov = [{"metodo": r["metodo"], "total": _f(r["total"]), "n": int(r["n"])} for r in proveedores]
    por_clase = {k: 0.0 for k in CLASES}
    gastos_por_metodo: dict[str, float] = {}
    for g in gastos:
        por_clase[g["clase"]] += _f(g["total"])
        gastos_por_metodo[g["metodo"]] = gastos_por_metodo.get(g["metodo"], 0.0) + _f(g["total"])
    total_entradas = sum(e["total"] for e in ent)
    total_proveedores = sum(p["total"] for p in prov)
    total_gastos = sum(por_clase.values())
    return {
        "entradas": ent,
        "total_entradas": total_entradas,
        "pagos_proveedores": prov,
        "total_proveedores": total_proveedores,
        "gastos_operativos": por_clase["operativo"],
        "inversiones": por_clase["inversion"],
        "abonos_credito": por_clase["credito"],
        "compras_como_gasto": por_clase["inventario"],
        "gastos_por_metodo": [
            {"metodo": k, "total": v}
            for k, v in sorted(gastos_por_metodo.items(), key=lambda x: -x[1])
        ],
        "total_salidas": total_proveedores + total_gastos,
        "flujo_neto": total_entradas - total_proveedores - total_gastos,
    }


# ───────────────────────── Historial mensual ─────────────────────────


def _inicio_mes(d: date, meses_atras: int) -> date:
    y, m = d.year, d.month - meses_atras
    while m <= 0:
        y, m = y - 1, m + 12
    return date(y, m, 1)


async def historial_mensual(db, meses: int = 6) -> list[dict]:
    """Un renglón por mes calendario (Bogotá), con las mismas reglas del estado."""
    hoy = datetime.now(_TZ).date()
    desde = _inicio_mes(hoy, meses - 1)
    since = datetime(desde.year, desde.month, desde.day, tzinfo=_TZ).astimezone(UTC)
    ventas = (
        (
            await db.execute(
                text(f"""
                    SELECT to_char(timezone('America/Bogota', o.occurred_at), 'YYYY-MM') AS mes,
                           sum(o.grand_total) AS ventas, count(*) AS n
                    FROM sales.orders o
                    WHERE o.occurred_at >= :since AND {VENTA_VALIDA}
                    GROUP BY 1
                """),
                {"since": since},
            )
        )
        .mappings()
        .all()
    )
    costos = (
        (
            await db.execute(
                text(f"""
                    SELECT to_char(timezone('America/Bogota', o.occurred_at), 'YYYY-MM') AS mes,
                           sum(i.unit_cost * i.quantity) AS costo
                    FROM sales.order_items i JOIN sales.orders o ON o.id = i.order_id
                    WHERE o.occurred_at >= :since AND {VENTA_VALIDA}
                    GROUP BY 1
                """),
                {"since": since},
            )
        )
        .mappings()
        .all()
    )
    gastos = (
        (
            await db.execute(
                text(f"""
                    SELECT to_char(fecha, 'YYYY-MM') AS mes, sum(monto) AS total
                    FROM finance.expenses
                    WHERE fecha >= :desde AND ({CLASE_GASTO_SQL}) = 'operativo'
                    GROUP BY 1
                """),
                {"desde": desde},
            )
        )
        .mappings()
        .all()
    )
    tarjeta = (
        (
            await db.execute(
                text(f"""
                    SELECT to_char(timezone('America/Bogota', o.occurred_at), 'YYYY-MM') AS mes,
                           sum(p.amount) AS monto, count(*) AS n
                    FROM sales.payments p JOIN sales.orders o ON o.id = p.order_id
                    WHERE p.method = 'Tarjeta' AND o.occurred_at >= :since AND {VENTA_VALIDA}
                    GROUP BY 1
                """),
                {"since": since},
            )
        )
        .mappings()
        .all()
    )
    v = {r["mes"]: r for r in ventas}
    c = {r["mes"]: _f(r["costo"]) for r in costos}
    g = {r["mes"]: _f(r["total"]) for r in gastos}
    t = {r["mes"]: r for r in tarjeta}
    out = []
    for k in range(meses):
        d = _inicio_mes(hoy, meses - 1 - k)
        mes = d.strftime("%Y-%m")
        ventas_netas = _f(v[mes]["ventas"]) if mes in v else 0.0
        costo = c.get(mes, 0.0)
        bruta = ventas_netas - costo
        gastos_op = g.get(mes, 0.0)
        comision = comision_tarjeta(_f(t[mes]["monto"]), int(t[mes]["n"])) if mes in t else 0.0
        neta = bruta - gastos_op - comision
        out.append(
            {
                "mes": mes,
                "dias": calendar.monthrange(d.year, d.month)[1]
                if d.month != hoy.month or d.year != hoy.year
                else hoy.day,
                "ventas_netas": ventas_netas,
                "n_ventas": int(v[mes]["n"]) if mes in v else 0,
                "costo_ventas": costo,
                "utilidad_bruta": bruta,
                "margen_bruto_pct": _pct(bruta, ventas_netas),
                "gastos_operativos": gastos_op,
                "comision_tarjeta": comision,
                "utilidad_neta": neta,
                "margen_neto_pct": _pct(neta, ventas_netas),
                "en_curso": mes == hoy.strftime("%Y-%m"),
            }
        )
    return out


# ───────────────────────── Todo junto ─────────────────────────


def _delta_pct(actual: float, anterior: float) -> float | None:
    if not anterior:
        return None
    return round((actual - anterior) / abs(anterior) * 100, 1)


async def estados_financieros(db, since: datetime, until: datetime) -> dict:
    actual = await estado_resultados(db, since, until)
    span = until - since
    anterior = await estado_resultados(db, since - span, since)
    bal = await balance(db)
    flujo = await flujo_caja(db, since, until)
    hist = await historial_mensual(db, 6)

    dias_venta = actual["periodo"]["dias_con_venta"] or 1
    costo_diario = actual["costo_ventas"] / dias_venta if actual["costo_ventas"] else 0.0
    inventario = bal["activos"]["inventario_costo"]
    indicadores = {
        "ventas_por_dia": round(actual["ventas_netas"] / dias_venta, 0),
        "ticket_promedio": actual["ticket_promedio"],
        "unidades_por_venta": round(actual["unidades"] / actual["n_ventas"], 1)
        if actual["n_ventas"]
        else 0.0,
        "dias_de_inventario": round(inventario / costo_diario, 0) if costo_diario else None,
        "rotacion_mensual": round(costo_diario * 30 / inventario, 2) if inventario else None,
        "punto_equilibrio": actual["punto_equilibrio"],
        "cobertura_pct": actual["cobertura_pct"],
        "gastos_sobre_ventas_pct": _pct(actual["gastos_operativos"], actual["ventas_netas"]),
    }

    alertas: list[dict] = []
    cal = actual["calidad"]
    if cal["unidades_sin_costo"]:
        alertas.append(
            {
                "nivel": "warning",
                "texto": f"{cal['unidades_sin_costo']} unidades vendidas sin costo registrado: "
                "el costo de ventas está subestimado en esas líneas.",
            }
        )
    if cal["lineas_bajo_costo"]:
        alertas.append(
            {
                "nivel": "danger",
                "texto": f"{cal['lineas_bajo_costo']} línea(s) vendidas por debajo del costo "
                f"(pérdida ${cal['perdida_bajo_costo']:,.0f}).".replace(",", "."),
            }
        )
    if cal["gastos_sin_clasificar"] > 0:
        alertas.append(
            {
                "nivel": "info",
                "texto": f"${cal['gastos_sin_clasificar']:,.0f} de gastos en 'Otros' o sin "
                "categoría: no se pueden analizar.".replace(",", "."),
            }
        )
    if bal["activos"]["productos_sin_costo"]:
        alertas.append(
            {
                "nivel": "warning",
                "texto": f"{bal['activos']['productos_sin_costo']} productos con existencias y "
                "costo $0: el inventario está subvalorado.",
            }
        )
    if bal["pasivos"]["proveedores_vencido"] > 0:
        alertas.append(
            {
                "nivel": "danger",
                "texto": f"${bal['pasivos']['proveedores_vencido']:,.0f} en facturas de "
                "proveedor ya vencidas.".replace(",", "."),
            }
        )
    if bal["activos"]["caja"] is None:
        alertas.append(
            {
                "nivel": "info",
                "texto": "No hay ningún cierre de caja cerrado: el balance no puede mostrar el "
                "efectivo en caja.",
            }
        )
    if actual["fuera_del_resultado"]["abonos_credito"]:
        alertas.append(
            {
                "nivel": "info",
                "texto": f"${actual['fuera_del_resultado']['abonos_credito']:,.0f} de abonos a "
                "crédito salen de caja pero no son gasto (si parte es interés, regístralo "
                "como gasto 'Financiero').".replace(",", "."),
            }
        )

    return {
        "resultados": actual,
        "anterior": anterior,
        "variacion": {
            k: _delta_pct(actual[k], anterior[k])
            for k in (
                "ventas_netas",
                "costo_ventas",
                "utilidad_bruta",
                "gastos_operativos",
                "utilidad_neta",
                "n_ventas",
                "ticket_promedio",
            )
        },
        "balance": bal,
        "flujo_caja": flujo,
        "historial": hist,
        "indicadores": indicadores,
        "alertas": alertas,
        "supuestos": [
            "El costo de la mercancía incluye el IVA pagado al proveedor (5 % o 19 %): la "
            "tienda no discrimina IVA en sus ventas, así que ese IVA es costo.",
            f"La comisión del datáfono es estimada: {get_settings().datafono_tasa_pct} % + "
            f"${get_settings().datafono_fijo_por_txn:,.0f} por transacción con tarjeta.".replace(
                ",", "."
            ),
            "Los pagos en línea por Bold no llevan comisión estimada todavía.",
            "El envío cobrado al cliente no es ingreso: se cruza con el registro de envíos.",
            "Inventario, cuentas por cobrar y por pagar son a la fecha de hoy, no al cierre "
            "del período.",
        ],
    }
