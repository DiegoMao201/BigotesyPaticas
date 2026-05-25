"""Endpoints financieros: gastos, cierres de caja, P&L, cash flow."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from app.deps import CurrentUser, DBSession, require_permission
from app.models.finance import CashClosing as CashClosingModel
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
    fecha: str
    status: str
    saldo_inicial: float
    gastos_efectivo: float
    ventas_por_metodo: dict[str, float]
    creditos_por_metodo: dict[str, float]
    total_ventas: float
    order_count: int
    ventas_efectivo: float
    creditos_efectivo: float
    saldo_final_efectivo: float
    saldo_contado: float | None
    diferencia: float | None
    notas: str | None
    closed_at: str | None
    closed_by: str | None


class CashClosingOpenPayload(BaseModel):
    fecha: date | None = None
    saldo_inicial: float = Field(default=0, ge=0)


class CashClosingClosePayload(BaseModel):
    saldo_contado: float = Field(ge=0)
    gastos_efectivo: float = Field(default=0, ge=0)
    notas: str | None = None


class CashClosingPatchPayload(BaseModel):
    gastos_efectivo: float | None = Field(default=None, ge=0)
    saldo_inicial: float | None = Field(default=None, ge=0)
    notas: str | None = None


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


# ────────────────── Cash Closings (real — finance.cash_closings) ──────────────────────

_TZ = "America/Bogota"
_TZINFO = ZoneInfo(_TZ)


def _today_in_business_tz() -> date:
    """Fecha de negocio en timezone local (no UTC del servidor)."""
    return datetime.now(_TZINFO).date()


async def _compute_live_totals(db: DBSession, fecha: date) -> dict[str, Any]:
    """Calcula totales en vivo desde sales.payments para una fecha."""
    method_rows = (await db.execute(
        text("""
            SELECT p.method, COALESCE(SUM(p.amount), 0) AS total
            FROM sales.payments p
            JOIN sales.orders o ON o.id = p.order_id
            WHERE DATE(o.occurred_at AT TIME ZONE 'America/Bogota') = :fecha
              AND o.status NOT IN ('cancelled')
            GROUP BY p.method
        """),
        {"fecha": fecha},
    )).all()
    ventas_por_metodo: dict[str, float] = {r.method: float(r.total) for r in method_rows}
    total_ventas = sum(ventas_por_metodo.values())

    refund_rows = (await db.execute(
        text("""
            SELECT COALESCE(o.payment_method, 'Otro') AS method,
                   COALESCE(SUM(o.grand_total), 0) AS total
            FROM sales.orders o
            WHERE DATE(o.occurred_at AT TIME ZONE 'America/Bogota') = :fecha
              AND o.status = 'refunded'
            GROUP BY o.payment_method
        """),
        {"fecha": fecha},
    )).all()
    creditos_por_metodo: dict[str, float] = {r.method: float(r.total) for r in refund_rows}

    order_count = (await db.execute(
        text("""
            SELECT COUNT(*) FROM sales.orders
            WHERE DATE(occurred_at AT TIME ZONE 'America/Bogota') = :fecha
              AND status NOT IN ('cancelled')
        """),
        {"fecha": fecha},
    )).scalar()

    return {
        "ventas_por_metodo": ventas_por_metodo,
        "creditos_por_metodo": creditos_por_metodo,
        "total_ventas": total_ventas,
        "order_count": int(order_count or 0),
    }


def _build_closing_out(closing: CashClosingModel, live: dict[str, Any]) -> CashClosingOut:
    ventas_pm = live["ventas_por_metodo"]
    creditos_pm = live["creditos_por_metodo"]
    ventas_efectivo = ventas_pm.get("Efectivo", 0.0)
    creditos_efectivo = creditos_pm.get("Efectivo", 0.0)
    saldo_final = float(closing.saldo_inicial) + ventas_efectivo - creditos_efectivo - float(closing.gastos_efectivo)
    return CashClosingOut(
        id=str(closing.id),
        fecha=str(closing.fecha),
        status=closing.status,
        saldo_inicial=float(closing.saldo_inicial),
        gastos_efectivo=float(closing.gastos_efectivo),
        ventas_por_metodo=ventas_pm,
        creditos_por_metodo=creditos_pm,
        total_ventas=live["total_ventas"],
        order_count=live["order_count"],
        ventas_efectivo=ventas_efectivo,
        creditos_efectivo=creditos_efectivo,
        saldo_final_efectivo=saldo_final,
        saldo_contado=float(closing.saldo_contado) if closing.saldo_contado is not None else None,
        diferencia=float(closing.diferencia) if closing.diferencia is not None else None,
        notas=closing.notas,
        closed_at=closing.closed_at.isoformat() if closing.closed_at else None,
        closed_by=closing.closed_by,
    )


@closings_router.get("/today", response_model=CashClosingOut)
async def get_today_closing(db: DBSession, user: CurrentUser):
    """Retorna el cierre de hoy (lo crea automáticamente si no existe)."""
    today = _today_in_business_tz()
    result = await db.execute(
        select(CashClosingModel).where(CashClosingModel.fecha == today)
    )
    closing = result.scalar_one_or_none()
    if not closing:
        prev_result = await db.execute(
            select(CashClosingModel)
            .where(CashClosingModel.fecha < today, CashClosingModel.status == "closed")
            .order_by(CashClosingModel.fecha.desc())
        )
        prev = prev_result.scalars().first()
        saldo_inicial = float(prev.saldo_final_efectivo or 0) if prev else 0.0
        closing = CashClosingModel(
            fecha=today,
            status="open",
            saldo_inicial=Decimal(str(saldo_inicial)),
            created_by=user.email,
        )
        db.add(closing)
        await db.commit()
        await db.refresh(closing)

    live = await _compute_live_totals(db, today)
    return _build_closing_out(closing, live)


@closings_router.get("", response_model=dict)
async def list_cash_closings(
    db: DBSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
):
    total_result = await db.execute(
        text("SELECT COUNT(*) FROM finance.cash_closings")
    )
    total = int(total_result.scalar() or 0)

    rows_result = await db.execute(
        select(CashClosingModel)
        .order_by(CashClosingModel.fecha.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    closings = rows_result.scalars().all()

    items = []
    for closing in closings:
        if closing.status == "open":
            live = await _compute_live_totals(db, closing.fecha)
        else:
            live = {
                "ventas_por_metodo": closing.snap_ventas_por_metodo or {},
                "creditos_por_metodo": closing.snap_creditos_por_metodo or {},
                "total_ventas": float(closing.snap_total_ventas or 0),
                "order_count": 0,
            }
        items.append(_build_closing_out(closing, live).model_dump())

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@closings_router.get("/{closing_id}", response_model=CashClosingOut)
async def get_cash_closing(closing_id: uuid.UUID, db: DBSession, user: CurrentUser):
    result = await db.execute(
        select(CashClosingModel).where(CashClosingModel.id == closing_id)
    )
    closing = result.scalar_one_or_none()
    if not closing:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    if closing.status == "open":
        live = await _compute_live_totals(db, closing.fecha)
    else:
        live = {
            "ventas_por_metodo": closing.snap_ventas_por_metodo or {},
            "creditos_por_metodo": closing.snap_creditos_por_metodo or {},
            "total_ventas": float(closing.snap_total_ventas or 0),
            "order_count": 0,
        }
    return _build_closing_out(closing, live)


@closings_router.post("", response_model=CashClosingOut, dependencies=[Depends(require_permission("finance:write"))])
async def open_cash_closing(
    payload: CashClosingOpenPayload,
    db: DBSession,
    user: CurrentUser,
):
    """Abre un cierre de caja para una fecha (hoy por defecto)."""
    target_date = payload.fecha or _today_in_business_tz()
    existing = (await db.execute(
        select(CashClosingModel).where(CashClosingModel.fecha == target_date)
    )).scalar_one_or_none()
    if existing:
        live = await _compute_live_totals(db, target_date)
        return _build_closing_out(existing, live)

    closing = CashClosingModel(
        fecha=target_date,
        status="open",
        saldo_inicial=Decimal(str(payload.saldo_inicial)),
        created_by=user.email,
    )
    db.add(closing)
    await db.commit()
    await db.refresh(closing)
    live = await _compute_live_totals(db, target_date)
    return _build_closing_out(closing, live)


@closings_router.patch("/{closing_id}", response_model=CashClosingOut, dependencies=[Depends(require_permission("finance:write"))])
async def patch_cash_closing(
    closing_id: uuid.UUID,
    payload: CashClosingPatchPayload,
    db: DBSession,
    user: CurrentUser,
):
    """Actualiza gastos en efectivo, saldo inicial o notas de un cierre abierto."""
    result = await db.execute(
        select(CashClosingModel).where(CashClosingModel.id == closing_id)
    )
    closing = result.scalar_one_or_none()
    if not closing:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    if closing.status == "closed":
        raise HTTPException(status_code=400, detail="El cierre ya está cerrado")
    if payload.gastos_efectivo is not None:
        closing.gastos_efectivo = Decimal(str(payload.gastos_efectivo))
    if payload.saldo_inicial is not None:
        closing.saldo_inicial = Decimal(str(payload.saldo_inicial))
    if payload.notas is not None:
        closing.notas = payload.notas
    closing.updated_by = user.email
    await db.commit()
    await db.refresh(closing)
    live = await _compute_live_totals(db, closing.fecha)
    return _build_closing_out(closing, live)


@closings_router.post("/{closing_id}/close", response_model=CashClosingOut, dependencies=[Depends(require_permission("finance:write"))])
async def close_cash_closing(
    closing_id: uuid.UUID,
    payload: CashClosingClosePayload,
    db: DBSession,
    user: CurrentUser,
):
    """Finaliza el cierre: guarda saldo_contado, diferencia y snapshot de ventas."""
    result = await db.execute(
        select(CashClosingModel).where(CashClosingModel.id == closing_id)
    )
    closing = result.scalar_one_or_none()
    if not closing:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    if closing.status == "closed":
        raise HTTPException(status_code=400, detail="El cierre ya está cerrado")

    live = await _compute_live_totals(db, closing.fecha)

    if payload.gastos_efectivo:
        closing.gastos_efectivo = Decimal(str(payload.gastos_efectivo))
    ventas_efectivo = live["ventas_por_metodo"].get("Efectivo", 0.0)
    creditos_efectivo = live["creditos_por_metodo"].get("Efectivo", 0.0)
    saldo_final = float(closing.saldo_inicial) + ventas_efectivo - creditos_efectivo - float(closing.gastos_efectivo)

    closing.snap_ventas_por_metodo = live["ventas_por_metodo"]
    closing.snap_creditos_por_metodo = live["creditos_por_metodo"]
    closing.snap_total_ventas = Decimal(str(live["total_ventas"]))
    closing.saldo_final_efectivo = Decimal(str(saldo_final))
    closing.saldo_contado = Decimal(str(payload.saldo_contado))
    closing.diferencia = Decimal(str(payload.saldo_contado)) - Decimal(str(saldo_final))
    closing.notas = payload.notas
    closing.status = "closed"
    closing.closed_at = datetime.utcnow()
    closing.closed_by = user.email
    closing.updated_by = user.email

    await db.commit()
    await db.refresh(closing)
    return _build_closing_out(closing, live)


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
