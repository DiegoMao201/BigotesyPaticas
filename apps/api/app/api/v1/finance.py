"""Endpoints financieros: gastos, cierres de caja, P&L, cash flow.

Lee de `ops.legacy_id_map` (entidad 'gasto', 'cierre_caja', 'proveedor_sku')
porque el ETL almacena estos registros como JSONB en `extra`.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from app.deps import CurrentUser, DBSession, require_permission
from app.models.ops import LegacyIdMap


router = APIRouter(prefix="/finance", tags=["finance"])
expenses_router = APIRouter(prefix="/expenses", tags=["finance"])
suppliers_router = APIRouter(prefix="/suppliers", tags=["finance"])
closings_router = APIRouter(prefix="/cash-closings", tags=["finance"])


# ────────────────── Schemas ──────────────────────

class ExpenseOut(BaseModel):
    id: str
    legacy_id: str
    fecha: str
    tipo: str
    categoria: str
    descripcion: str
    monto: float
    metodo_pago: str
    banco_origen: str = ""


class ExpenseCreate(BaseModel):
    fecha: date
    tipo: str = "Operativo"
    categoria: str = "General"
    descripcion: str = ""
    monto: float = Field(gt=0)
    metodo_pago: str = "Efectivo"
    banco_origen: str = ""


class CashClosingOut(BaseModel):
    id: str
    legacy_id: str
    fecha: str
    ventas_efectivo: float = 0
    gastos_efectivo: float = 0
    saldo_inicial: float = 0
    saldo_final: float = 0
    diferencia: float = 0
    notas: str = ""


class SupplierOut(BaseModel):
    id_proveedor: str
    nombre_proveedor: str
    sku_proveedor: str
    sku_interno: str = ""
    factor_pack: float = 1
    costo_unidad: float = 0


class FinanceSummary(BaseModel):
    period_start: date
    period_end: date
    revenue: float = 0
    cogs: float = 0
    gross_profit: float = 0
    gross_margin_pct: float = 0
    expenses_total: float = 0
    net_profit: float = 0
    net_margin_pct: float = 0
    expenses_by_category: list[dict[str, Any]] = []
    revenue_by_method: list[dict[str, Any]] = []
    daily_cashflow: list[dict[str, Any]] = []


# ────────────────── Helpers ──────────────────────

def _f(x: Any, default: float = 0.0) -> float:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


# ────────────────── Expenses ──────────────────────

@expenses_router.get("", response_model=dict)
async def list_expenses(
    db: DBSession,
    user: CurrentUser,
    start: date | None = Query(None),
    end: date | None = Query(None),
    categoria: str | None = None,
    metodo_pago: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    stmt = select(LegacyIdMap).where(LegacyIdMap.entity == "gasto")
    rows = (await db.execute(stmt)).scalars().all()

    items = []
    total_monto = 0.0
    for r in rows:
        e = r.extra or {}
        f = str(e.get("fecha", ""))
        try:
            fecha_obj = datetime.fromisoformat(f[:10]).date() if f else None
        except Exception:
            fecha_obj = None
        if start and fecha_obj and fecha_obj < start:
            continue
        if end and fecha_obj and fecha_obj > end:
            continue
        if categoria and str(e.get("categoria", "")).lower() != categoria.lower():
            continue
        if metodo_pago and str(e.get("metodo_pago", "")).lower() != metodo_pago.lower():
            continue
        monto = _f(e.get("monto"))
        total_monto += monto
        items.append({
            "id": str(r.id),
            "legacy_id": r.legacy_id,
            "fecha": f[:10] if f else "",
            "tipo": str(e.get("tipo", "")),
            "categoria": str(e.get("categoria", "")),
            "descripcion": str(e.get("descripcion", "")),
            "monto": monto,
            "metodo_pago": str(e.get("metodo_pago", "")),
            "banco_origen": str(e.get("banco_origen", "")),
        })

    items.sort(key=lambda x: x["fecha"], reverse=True)
    total = len(items)
    start_idx = (page - 1) * page_size
    paged = items[start_idx:start_idx + page_size]

    return {
        "items": paged,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_monto": total_monto,
    }


@expenses_router.post("", response_model=ExpenseOut, dependencies=[Depends(require_permission("finance:write"))])
async def create_expense(
    payload: ExpenseCreate,
    db: DBSession,
    user: CurrentUser,
):
    legacy_id = f"GASTO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    extra = {
        "fecha": payload.fecha.isoformat(),
        "tipo": payload.tipo,
        "categoria": payload.categoria,
        "descripcion": payload.descripcion,
        "monto": payload.monto,
        "metodo_pago": payload.metodo_pago,
        "banco_origen": payload.banco_origen,
        "created_by": user.email,
    }
    record = LegacyIdMap(
        entity="gasto",
        legacy_id=legacy_id,
        new_id=uuid.uuid4(),
        extra=extra,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return ExpenseOut(
        id=str(record.id),
        legacy_id=legacy_id,
        fecha=payload.fecha.isoformat(),
        tipo=payload.tipo,
        categoria=payload.categoria,
        descripcion=payload.descripcion,
        monto=payload.monto,
        metodo_pago=payload.metodo_pago,
        banco_origen=payload.banco_origen,
    )


@expenses_router.get("/categories")
async def list_expense_categories(db: DBSession, user: CurrentUser):
    rows = (await db.execute(select(LegacyIdMap).where(LegacyIdMap.entity == "gasto"))).scalars().all()
    cats: dict[str, dict] = {}
    for r in rows:
        e = r.extra or {}
        cat = str(e.get("categoria", "Sin categoría")) or "Sin categoría"
        if cat not in cats:
            cats[cat] = {"name": cat, "count": 0, "total": 0.0}
        cats[cat]["count"] += 1
        cats[cat]["total"] += _f(e.get("monto"))
    return sorted(cats.values(), key=lambda x: -x["total"])


# ────────────────── Cash Closings ──────────────────────

@closings_router.get("", response_model=dict)
async def list_cash_closings(
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
):
    rows = (await db.execute(
        select(LegacyIdMap).where(LegacyIdMap.entity == "cierre_caja")
    )).scalars().all()

    items = []
    for r in rows:
        e = r.extra or {}
        f = str(e.get("fecha", ""))
        items.append({
            "id": str(r.id),
            "legacy_id": r.legacy_id,
            "fecha": f[:10] if f else "",
            "ventas_efectivo": _f(e.get("ventas_efectivo")),
            "gastos_efectivo": _f(e.get("gastos_efectivo")),
            "saldo_inicial": _f(e.get("saldo_inicial")),
            "saldo_final": _f(e.get("saldo_final")),
            "diferencia": _f(e.get("diferencia")),
            "notas": str(e.get("notas", "")),
        })
    items.sort(key=lambda x: x["fecha"], reverse=True)
    total = len(items)
    start_idx = (page - 1) * page_size
    return {
        "items": items[start_idx:start_idx + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ────────────────── Suppliers ──────────────────────

@suppliers_router.get("", response_model=dict)
async def list_suppliers(
    db: DBSession,
    user: CurrentUser,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    rows = (await db.execute(
        select(LegacyIdMap).where(LegacyIdMap.entity == "proveedor_sku")
    )).scalars().all()

    items = []
    for r in rows:
        e = r.extra or {}
        item = {
            "id_proveedor": str(e.get("id_proveedor", "")),
            "nombre_proveedor": str(e.get("nombre_proveedor", "")),
            "sku_proveedor": str(e.get("sku_proveedor", "")),
            "sku_interno": str(e.get("sku_interno", "")),
            "factor_pack": _f(e.get("factor_pack"), 1),
            "costo_unidad": _f(e.get("costo_unidad")),
        }
        if q:
            ql = q.lower()
            text_blob = " ".join(str(v).lower() for v in item.values())
            if ql not in text_blob:
                continue
        items.append(item)

    # Agrupar por proveedor para vista resumen
    items.sort(key=lambda x: x["nombre_proveedor"])
    total = len(items)
    start_idx = (page - 1) * page_size
    return {
        "items": items[start_idx:start_idx + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@suppliers_router.get("/grouped")
async def suppliers_grouped(db: DBSession, user: CurrentUser):
    """Lista proveedores únicos con conteo de SKUs."""
    rows = (await db.execute(
        select(LegacyIdMap).where(LegacyIdMap.entity == "proveedor_sku")
    )).scalars().all()
    by_prov: dict[str, dict] = {}
    for r in rows:
        e = r.extra or {}
        nom = str(e.get("nombre_proveedor", "Sin nombre")) or "Sin nombre"
        if nom not in by_prov:
            by_prov[nom] = {
                "nombre_proveedor": nom,
                "id_proveedor": str(e.get("id_proveedor", "")),
                "sku_count": 0,
                "skus": [],
            }
        by_prov[nom]["sku_count"] += 1
        by_prov[nom]["skus"].append({
            "sku_proveedor": str(e.get("sku_proveedor", "")),
            "sku_interno": str(e.get("sku_interno", "")),
            "costo": _f(e.get("costo_unidad")),
        })
    return sorted(by_prov.values(), key=lambda x: -x["sku_count"])


# ────────────────── Finance Summary (P&L) ──────────────────────

@router.get("/summary", response_model=FinanceSummary)
async def finance_summary(
    db: DBSession,
    user: CurrentUser,
    start: date | None = None,
    end: date | None = None,
):
    today = date.today()
    if not end:
        end = today
    if not start:
        start = today.replace(day=1)

    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())

    # Revenue + COGS via raw SQL
    rev_row = (await db.execute(
        text(
            """
            SELECT 
              COALESCE(SUM(o.grand_total), 0) AS revenue,
              COALESCE(SUM(oi.unit_cost * oi.quantity), 0) AS cogs
            FROM sales.orders o
            LEFT JOIN sales.order_items oi ON oi.order_id = o.id
            WHERE o.occurred_at BETWEEN :start_dt AND :end_dt
              AND COALESCE(o.status, '') <> 'cancelled'
            """
        ),
        {"start_dt": start_dt, "end_dt": end_dt},
    )).one()
    revenue = float(rev_row.revenue or 0)
    cogs = float(rev_row.cogs or 0)

    # Expenses
    exp_rows = (await db.execute(
        select(LegacyIdMap).where(LegacyIdMap.entity == "gasto")
    )).scalars().all()
    expenses_total = 0.0
    by_cat: dict[str, float] = {}
    for r in exp_rows:
        e = r.extra or {}
        f = str(e.get("fecha", ""))[:10]
        try:
            d = datetime.fromisoformat(f).date()
        except Exception:
            continue
        if d < start or d > end:
            continue
        m = _f(e.get("monto"))
        expenses_total += m
        cat = str(e.get("categoria", "Sin categoría")) or "Sin categoría"
        by_cat[cat] = by_cat.get(cat, 0) + m

    # Revenue by payment method
    method_rows = (await db.execute(
        text(
            """
            SELECT p.method, COALESCE(SUM(p.amount), 0) as total
            FROM sales.payments p
            JOIN sales.orders o ON o.id = p.order_id
            WHERE o.occurred_at BETWEEN :start_dt AND :end_dt
              AND COALESCE(o.status, '') <> 'cancelled'
            GROUP BY p.method
            ORDER BY total DESC
            """
        ),
        {"start_dt": start_dt, "end_dt": end_dt},
    )).all()
    revenue_by_method = [{"method": r.method or "Sin método", "total": float(r.total)} for r in method_rows]

    # Daily cashflow
    daily_rows = (await db.execute(
        text(
            """
            SELECT DATE(o.occurred_at) AS d, COALESCE(SUM(o.grand_total), 0) AS revenue
            FROM sales.orders o
            WHERE o.occurred_at BETWEEN :start_dt AND :end_dt
              AND COALESCE(o.status, '') <> 'cancelled'
            GROUP BY DATE(o.occurred_at)
            ORDER BY d
            """
        ),
        {"start_dt": start_dt, "end_dt": end_dt},
    )).all()
    daily = [{"date": str(r.d), "revenue": float(r.revenue), "expenses": 0.0} for r in daily_rows]
    # Add daily expenses
    daily_map = {d["date"]: d for d in daily}
    for r in exp_rows:
        e = r.extra or {}
        f = str(e.get("fecha", ""))[:10]
        try:
            d = datetime.fromisoformat(f).date()
        except Exception:
            continue
        if d < start or d > end:
            continue
        ds = str(d)
        if ds not in daily_map:
            daily_map[ds] = {"date": ds, "revenue": 0.0, "expenses": 0.0}
        daily_map[ds]["expenses"] += _f(e.get("monto"))
    daily_sorted = sorted(daily_map.values(), key=lambda x: x["date"])

    gross_profit = revenue - cogs
    net_profit = gross_profit - expenses_total
    return FinanceSummary(
        period_start=start,
        period_end=end,
        revenue=revenue,
        cogs=cogs,
        gross_profit=gross_profit,
        gross_margin_pct=(gross_profit / revenue * 100) if revenue else 0,
        expenses_total=expenses_total,
        net_profit=net_profit,
        net_margin_pct=(net_profit / revenue * 100) if revenue else 0,
        expenses_by_category=sorted(
            [{"category": k, "total": v} for k, v in by_cat.items()],
            key=lambda x: -x["total"],
        ),
        revenue_by_method=revenue_by_method,
        daily_cashflow=daily_sorted,
    )
