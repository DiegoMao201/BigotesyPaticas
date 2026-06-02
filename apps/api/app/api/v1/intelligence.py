"""Centro de Inteligencia — recompra predictiva, retención y capital atrapado.

Pensado para crecer una tienda petshop: detectar a quién contactar HOY para
vender más (recompra de alimento), qué clientes valiosos se están enfriando, y
qué capital está atrapado en inventario sin rotación.
"""
from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from math import ceil
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.deps import DBSession, require_permission
from app.models.catalog import Product
from app.models.crm import Customer
from app.models.inventory import Stock
from app.models.purchasing import Supplier, SupplierSkuMap
from app.models.sales import Order, OrderItem

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────
def _normalize_phone_co(phone: str | None) -> str | None:
    """Devuelve el teléfono en formato internacional Colombia (57XXXXXXXXXX)."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None
    digits = digits.lstrip("0")
    if digits.startswith("57") and len(digits) >= 12:
        return digits
    if len(digits) == 10:  # celular colombiano local
        return f"57{digits}"
    return digits


def _wa_link(phone: str | None, message: str) -> str | None:
    norm = _normalize_phone_co(phone)
    if not norm:
        return None
    return f"https://wa.me/{norm}?text={quote(message)}"


# ─────────────────────────────────────────────────────────────
#  Schemas
# ─────────────────────────────────────────────────────────────
class RepurchaseItem(BaseModel):
    customer_id: str
    name: str
    phone: str | None = None
    last_purchase: str | None = None
    days_since: int
    avg_interval_days: int
    days_overdue: int  # >0 = ya pasó la fecha estimada de recompra
    orders: int
    monetary: float
    favorite_product: str | None = None
    urgency: str  # "vencido" | "hoy" | "proximo"
    whatsapp_url: str | None = None


class AtRiskItem(BaseModel):
    customer_id: str
    name: str
    phone: str | None = None
    last_purchase: str | None = None
    days_since: int
    orders: int
    monetary: float
    segment: str | None = None
    whatsapp_url: str | None = None


class DeadStockItem(BaseModel):
    product_id: str
    sku: str
    name: str
    available: int
    unit_cost: float
    trapped_capital: float
    days_no_sale: int | None = None


class IntelSummary(BaseModel):
    customers_total: int
    customers_active_90d: int
    repurchase_due: int
    repurchase_revenue_opportunity: float
    at_risk_count: int
    at_risk_value: float
    dead_stock_count: int
    trapped_capital: float


class IntelligenceOut(BaseModel):
    generated_at: str
    summary: IntelSummary
    repurchase: list[RepurchaseItem]
    at_risk: list[AtRiskItem]
    dead_stock: list[DeadStockItem]


@router.get(
    "/overview",
    response_model=IntelligenceOut,
    dependencies=[Depends(require_permission("analytics:read"))],
)
async def intelligence_overview(
    db: DBSession,
    at_risk_days: int = Query(60, ge=20, le=365),
    dead_stock_days: int = Query(90, ge=30, le=365),
) -> IntelligenceOut:
    now = datetime.now(UTC)

    valid_status = ["cancelled", "refunded"]

    # ── Agregado por cliente (recencia/frecuencia/monetario) ──
    agg_rows = (
        await db.execute(
            select(
                Order.customer_id,
                func.count(Order.id).label("orders"),
                func.min(Order.occurred_at).label("first_at"),
                func.max(Order.occurred_at).label("last_at"),
                func.coalesce(func.sum(Order.grand_total), 0).label("monetary"),
            )
            .where(Order.customer_id.isnot(None))
            .where(Order.status.notin_(valid_status))
            .group_by(Order.customer_id)
        )
    ).all()

    cust_ids = [r.customer_id for r in agg_rows]
    customers: dict = {}
    if cust_ids:
        crows = (
            await db.execute(
                select(Customer.id, Customer.full_name, Customer.phone, Customer.rfm_segment)
                .where(Customer.id.in_(cust_ids))
            )
        ).all()
        customers = {c.id: c for c in crows}

    # ── Producto favorito por cliente (mayor cantidad histórica) ──
    fav: dict = {}
    if cust_ids:
        fav_rows = (
            await db.execute(
                select(
                    Order.customer_id,
                    OrderItem.name_snapshot,
                    func.sum(OrderItem.quantity).label("qty"),
                )
                .join(OrderItem, OrderItem.order_id == Order.id)
                .where(Order.customer_id.in_(cust_ids))
                .where(Order.status.notin_(valid_status))
                .group_by(Order.customer_id, OrderItem.name_snapshot)
            )
        ).all()
        best: dict = {}
        for r in fav_rows:
            cur = best.get(r.customer_id)
            if cur is None or (r.qty or 0) > cur[1]:
                best[r.customer_id] = (r.name_snapshot, r.qty or 0)
        fav = {k: v[0] for k, v in best.items()}

    repurchase: list[RepurchaseItem] = []
    at_risk: list[AtRiskItem] = []
    active_90 = 0
    repurchase_opportunity = 0.0
    at_risk_value = 0.0

    for r in agg_rows:
        cust = customers.get(r.customer_id)
        if cust is None:
            continue
        last_at = r.last_at
        first_at = r.first_at
        if last_at is None:
            continue
        if last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=UTC)
        if first_at is not None and first_at.tzinfo is None:
            first_at = first_at.replace(tzinfo=UTC)

        days_since = (now - last_at).days
        orders = int(r.orders or 0)
        monetary = float(r.monetary or 0)
        avg_ticket = monetary / orders if orders else 0.0

        if days_since <= 90:
            active_90 += 1

        # Intervalo promedio entre compras (solo con ≥2 compras)
        if orders >= 2 and first_at is not None:
            span_days = max((last_at - first_at).days, 1)
            avg_interval = max(round(span_days / (orders - 1)), 7)
            days_overdue = days_since - avg_interval
            # Ventana: por recomprar pronto (faltan ≤7 días) o vencido,
            # pero no clientes ya perdidos (>2.5x el intervalo).
            if days_overdue >= -7 and days_since <= avg_interval * 2.5:
                if days_overdue > 0:
                    urgency = "vencido"
                elif days_overdue >= -2:
                    urgency = "hoy"
                else:
                    urgency = "proximo"
                fav_prod = fav.get(r.customer_id)
                first_name = cust.full_name.split(" ")[0] if cust.full_name else "Hola"
                if fav_prod:
                    msg = (
                        f"¡Hola {first_name}! 🐾 En Bigotes y Paticas notamos que quizá "
                        f"ya se te está acabando *{fav_prod}*. ¿Te lo reservamos y te lo "
                        f"llevamos a domicilio?"
                    )
                else:
                    msg = (
                        f"¡Hola {first_name}! 🐾 Te extrañamos en Bigotes y Paticas. "
                        f"¿Necesitas algo para tu mascota? Te lo llevamos a domicilio."
                    )
                repurchase.append(
                    RepurchaseItem(
                        customer_id=str(r.customer_id),
                        name=cust.full_name,
                        phone=cust.phone,
                        last_purchase=last_at.date().isoformat(),
                        days_since=days_since,
                        avg_interval_days=avg_interval,
                        days_overdue=days_overdue,
                        orders=orders,
                        monetary=monetary,
                        favorite_product=fav_prod,
                        urgency=urgency,
                        whatsapp_url=_wa_link(cust.phone, msg),
                    )
                )
                repurchase_opportunity += avg_ticket

        # En riesgo: cliente valioso (≥2 compras) inactivo y NO ya capturado arriba
        if orders >= 2 and days_since >= at_risk_days:
            first_name = cust.full_name.split(" ")[0] if cust.full_name else "Hola"
            msg = (
                f"¡Hola {first_name}! 🐾 Hace rato no te vemos por Bigotes y Paticas. "
                f"Tenemos novedades para tu mascota y un detalle especial para ti. "
                f"¿Pasas o te llevamos a domicilio?"
            )
            at_risk.append(
                AtRiskItem(
                    customer_id=str(r.customer_id),
                    name=cust.full_name,
                    phone=cust.phone,
                    last_purchase=last_at.date().isoformat(),
                    days_since=days_since,
                    orders=orders,
                    monetary=monetary,
                    segment=cust.rfm_segment,
                    whatsapp_url=_wa_link(cust.phone, msg),
                )
            )
            at_risk_value += monetary

    # Orden: vencidos primero, luego por mayor atraso y valor
    urgency_rank = {"vencido": 0, "hoy": 1, "proximo": 2}
    repurchase.sort(key=lambda x: (urgency_rank.get(x.urgency, 9), -x.days_overdue, -x.monetary))
    at_risk.sort(key=lambda x: -x.monetary)
    repurchase = repurchase[:100]
    at_risk = at_risk[:100]

    # ── Capital atrapado: stock con costo que no rota ──
    last_sale_sub = (
        select(
            OrderItem.product_id.label("pid"),
            func.max(Order.occurred_at).label("last_sale"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status.notin_(valid_status))
        .group_by(OrderItem.product_id)
        .subquery()
    )
    stock_rows = (
        await db.execute(
            select(
                Product.id,
                Product.sku,
                Product.name,
                func.coalesce(Product.cost, 0).label("cost"),
                func.coalesce(func.sum(Stock.quantity - Stock.reserved), 0).label("available"),
                last_sale_sub.c.last_sale,
            )
            .join(Stock, Stock.product_id == Product.id)
            .join(last_sale_sub, last_sale_sub.c.pid == Product.id, isouter=True)
            .where(Product.is_active == True)  # noqa: E712
            .where(Product.deleted_at == None)  # noqa: E711
            .group_by(Product.id, Product.sku, Product.name, Product.cost, last_sale_sub.c.last_sale)
        )
    ).all()

    dead_stock: list[DeadStockItem] = []
    trapped_capital = 0.0
    for r in stock_rows:
        available = int(r.available or 0)
        if available <= 0:
            continue
        last_sale = r.last_sale
        if last_sale is not None and last_sale.tzinfo is None:
            last_sale = last_sale.replace(tzinfo=UTC)
        days_no_sale = (now - last_sale).days if last_sale is not None else None
        is_dead = days_no_sale is None or days_no_sale >= dead_stock_days
        if not is_dead:
            continue
        cost = float(r.cost or 0)
        trapped = cost * available
        if trapped <= 0:
            continue
        trapped_capital += trapped
        dead_stock.append(
            DeadStockItem(
                product_id=str(r.id),
                sku=r.sku,
                name=r.name,
                available=available,
                unit_cost=cost,
                trapped_capital=round(trapped, 2),
                days_no_sale=days_no_sale,
            )
        )
    dead_stock.sort(key=lambda x: -x.trapped_capital)
    dead_stock_full_count = len(dead_stock)
    dead_stock = dead_stock[:100]

    customers_total = (
        await db.execute(
            select(func.count(Customer.id)).where(Customer.deleted_at == None)  # noqa: E711
        )
    ).scalar_one()

    return IntelligenceOut(
        generated_at=now.isoformat(),
        summary=IntelSummary(
            customers_total=int(customers_total or 0),
            customers_active_90d=active_90,
            repurchase_due=len(repurchase),
            repurchase_revenue_opportunity=round(repurchase_opportunity, 2),
            at_risk_count=len(at_risk),
            at_risk_value=round(at_risk_value, 2),
            dead_stock_count=dead_stock_full_count,
            trapped_capital=round(trapped_capital, 2),
        ),
        repurchase=repurchase,
        at_risk=at_risk,
        dead_stock=dead_stock,
    )


# ═══════════════════════════════════════════════════════════════
#  P1 — COMBOS / MARKET BASKET ("se vende junto con")
# ═══════════════════════════════════════════════════════════════
class ComboSuggestion(BaseModel):
    product_id: str
    sku: str
    name: str
    price: float
    times_together: int
    stock: int


@router.get(
    "/frequently-bought",
    response_model=list[ComboSuggestion],
    dependencies=[Depends(require_permission("analytics:read"))],
)
async def frequently_bought(
    db: DBSession,
    product_ids: str = Query(..., description="IDs de producto separados por coma (carrito)"),
    limit: int = Query(6, ge=1, le=20),
) -> list[ComboSuggestion]:
    """Productos que históricamente se compran junto con los del carrito."""
    import uuid as _uuid

    ids: list = []
    for raw in product_ids.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            ids.append(_uuid.UUID(raw))
        except ValueError:
            continue
    if not ids:
        return []

    # Órdenes que contienen alguno de los productos del carrito
    order_ids_sub = (
        select(OrderItem.order_id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(OrderItem.product_id.in_(ids))
        .where(Order.status.notin_(["cancelled", "refunded"]))
        .distinct()
    )

    rows = (
        await db.execute(
            select(
                OrderItem.product_id,
                func.count(func.distinct(OrderItem.order_id)).label("together"),
            )
            .where(OrderItem.order_id.in_(order_ids_sub))
            .where(OrderItem.product_id.notin_(ids))
            .group_by(OrderItem.product_id)
            .order_by(func.count(func.distinct(OrderItem.order_id)).desc())
            .limit(limit * 2)
        )
    ).all()

    if not rows:
        return []

    cand_ids = [r.product_id for r in rows]
    together_map = {r.product_id: int(r.together or 0) for r in rows}

    prods = (
        await db.execute(
            select(Product.id, Product.sku, Product.name, Product.price, Product.is_active)
            .where(Product.id.in_(cand_ids))
            .where(Product.deleted_at == None)  # noqa: E711
            .where(Product.is_active == True)  # noqa: E712
        )
    ).all()

    stock_rows = (
        await db.execute(
            select(Stock.product_id, func.coalesce(func.sum(Stock.quantity - Stock.reserved), 0))
            .where(Stock.product_id.in_(cand_ids))
            .group_by(Stock.product_id)
        )
    ).all()
    stock_map = {pid: int(q or 0) for pid, q in stock_rows}

    out = [
        ComboSuggestion(
            product_id=str(p.id),
            sku=p.sku,
            name=p.name,
            price=float(p.price or 0),
            times_together=together_map.get(p.id, 0),
            stock=stock_map.get(p.id, 0),
        )
        for p in prods
    ]
    out.sort(key=lambda x: -x.times_together)
    return out[:limit]


# ═══════════════════════════════════════════════════════════════
#  P2/P6 — VELOCIDAD, QUIEBRE DE STOCK Y REABASTECIMIENTO
# ═══════════════════════════════════════════════════════════════
async def _velocity_rows(db: DBSession, days: int) -> list[dict]:
    """Velocidad de venta y cobertura por producto (con proveedor asociado)."""
    now = datetime.now(UTC)
    since = now - timedelta(days=days)

    sales_rows = (
        await db.execute(
            select(
                OrderItem.product_id,
                func.coalesce(func.sum(OrderItem.quantity), 0).label("units"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.occurred_at >= since)
            .where(Order.status.notin_(["cancelled", "refunded"]))
            .group_by(OrderItem.product_id)
        )
    ).all()
    sold_map = {pid: float(u or 0) for pid, u in sales_rows}

    # Último proveedor por producto
    sup_rows = (
        await db.execute(
            select(
                SupplierSkuMap.product_id,
                SupplierSkuMap.supplier_id,
                Supplier.name,
                Supplier.phone,
                SupplierSkuMap.last_seen_at,
                SupplierSkuMap.created_at,
            )
            .join(Supplier, Supplier.id == SupplierSkuMap.supplier_id)
            .where(Supplier.is_active == True)  # noqa: E712
        )
    ).all()
    _min = datetime.min.replace(tzinfo=UTC)
    sup_best: dict = {}
    for pid, sid, sname, sphone, last_seen, created in sup_rows:
        key = last_seen or created or _min
        if key.tzinfo is None:
            key = key.replace(tzinfo=UTC)
        cur = sup_best.get(pid)
        if cur is None or key >= cur[0]:
            sup_best[pid] = (key, str(sid), sname, sphone)

    prod_rows = (
        await db.execute(
            select(
                Product.id,
                Product.sku,
                Product.name,
                func.coalesce(Product.cost, 0),
                func.coalesce(Product.price, 0),
                func.coalesce(func.sum(Stock.quantity - Stock.reserved), 0).label("available"),
            )
            .join(Stock, Stock.product_id == Product.id, isouter=True)
            .where(Product.is_active == True)  # noqa: E712
            .where(Product.deleted_at == None)  # noqa: E711
            .group_by(Product.id, Product.sku, Product.name, Product.cost, Product.price)
        )
    ).all()

    out: list[dict] = []
    for r in prod_rows:
        available = int(r.available or 0)
        sold = sold_map.get(r.id, 0.0)
        velocity = sold / float(days)  # unidades/día
        days_cover = (available / velocity) if velocity > 0 else None
        sup = sup_best.get(r.id)
        out.append({
            "product_id": str(r.id),
            "sku": r.sku,
            "name": r.name,
            "cost": float(r[3] or 0),
            "price": float(r[4] or 0),
            "available": available,
            "sold_period": sold,
            "velocity": velocity,
            "days_cover": days_cover,
            "supplier_id": sup[1] if sup else None,
            "supplier_name": sup[2] if sup else None,
            "supplier_phone": sup[3] if sup else None,
        })
    return out


class StockoutItem(BaseModel):
    product_id: str
    sku: str
    name: str
    available: int
    velocity: float           # unidades/día
    days_cover: float | None  # días hasta agotarse
    stockout_date: str | None
    suggested_reorder: int    # para cubrir target_days
    supplier_name: str | None = None
    level: str                # "agotado" | "critico" | "bajo" | "ok"


class StockoutForecastOut(BaseModel):
    generated_at: str
    target_days: int
    summary: dict
    items: list[StockoutItem]


@router.get(
    "/stockout-forecast",
    response_model=StockoutForecastOut,
    dependencies=[Depends(require_permission("analytics:read"))],
)
async def stockout_forecast(
    db: DBSession,
    velocity_days: int = Query(30, ge=7, le=120),
    target_days: int = Query(15, ge=5, le=60),
    horizon_days: int = Query(21, ge=5, le=90, description="Solo productos que se agotan dentro de N días"),
) -> StockoutForecastOut:
    now = datetime.now(UTC)
    rows = await _velocity_rows(db, velocity_days)

    items: list[StockoutItem] = []
    agotado = critico = bajo = 0
    for r in rows:
        velocity = r["velocity"]
        available = r["available"]
        if velocity <= 0:
            continue  # sin rotación → no es riesgo de quiebre
        days_cover = r["days_cover"]
        if days_cover is None or days_cover > horizon_days:
            continue
        stockout_dt = (now + timedelta(days=days_cover)).date().isoformat() if days_cover is not None else None
        suggested = max(0, ceil(velocity * target_days - available))
        if available <= 0:
            level = "agotado"; agotado += 1
        elif days_cover <= 5:
            level = "critico"; critico += 1
        else:
            level = "bajo"; bajo += 1
        items.append(StockoutItem(
            product_id=r["product_id"],
            sku=r["sku"],
            name=r["name"],
            available=available,
            velocity=round(velocity, 2),
            days_cover=round(days_cover, 1) if days_cover is not None else None,
            stockout_date=stockout_dt,
            suggested_reorder=suggested,
            supplier_name=r["supplier_name"],
            level=level,
        ))
    items.sort(key=lambda x: (x.days_cover if x.days_cover is not None else 9999))

    return StockoutForecastOut(
        generated_at=now.isoformat(),
        target_days=target_days,
        summary={
            "at_risk": len(items),
            "agotado": agotado,
            "critico": critico,
            "bajo": bajo,
        },
        items=items[:200],
    )


class ReplenishLine(BaseModel):
    product_id: str
    sku: str
    name: str
    available: int
    velocity: float
    days_cover: float | None
    suggested_qty: int
    unit_cost: float
    line_cost: float


class ReplenishSupplier(BaseModel):
    supplier_id: str | None
    supplier_name: str
    supplier_phone: str | None
    lines: list[ReplenishLine]
    total_units: int
    total_cost: float
    whatsapp_url: str | None = None


class ReplenishmentOut(BaseModel):
    generated_at: str
    target_days: int
    total_cost: float
    suppliers: list[ReplenishSupplier]


@router.get(
    "/replenishment",
    response_model=ReplenishmentOut,
    dependencies=[Depends(require_permission("analytics:read"))],
)
async def replenishment(
    db: DBSession,
    velocity_days: int = Query(30, ge=7, le=120),
    target_days: int = Query(15, ge=5, le=60),
    coverage_threshold_days: int = Query(15, ge=5, le=60, description="Reabastecer si cobertura ≤ N días"),
) -> ReplenishmentOut:
    now = datetime.now(UTC)
    rows = await _velocity_rows(db, velocity_days)

    groups: dict = {}
    for r in rows:
        velocity = r["velocity"]
        if velocity <= 0:
            continue
        days_cover = r["days_cover"]
        # Necesita reposición si cobertura por debajo del umbral
        if days_cover is not None and days_cover > coverage_threshold_days:
            continue
        suggested = max(0, ceil(velocity * target_days - r["available"]))
        if suggested <= 0:
            continue
        key = r["supplier_id"] or "__none__"
        if key not in groups:
            groups[key] = {
                "supplier_id": r["supplier_id"],
                "supplier_name": r["supplier_name"] or "Sin proveedor asignado",
                "supplier_phone": r["supplier_phone"],
                "lines": [],
            }
        unit_cost = r["cost"]
        groups[key]["lines"].append(ReplenishLine(
            product_id=r["product_id"],
            sku=r["sku"],
            name=r["name"],
            available=r["available"],
            velocity=round(velocity, 2),
            days_cover=round(days_cover, 1) if days_cover is not None else None,
            suggested_qty=suggested,
            unit_cost=unit_cost,
            line_cost=round(unit_cost * suggested, 2),
        ))

    suppliers_out: list[ReplenishSupplier] = []
    grand_total = 0.0
    for g in groups.values():
        lines = sorted(g["lines"], key=lambda x: (x.days_cover if x.days_cover is not None else 9999))
        total_units = sum(line.suggested_qty for line in lines)
        total_cost = round(sum(line.line_cost for line in lines), 2)
        grand_total += total_cost
        # Mensaje WhatsApp con el pedido
        msg_lines = ["🐾 *Bigotes y Paticas* — Pedido de reabastecimiento", ""]
        for line in lines[:50]:
            msg_lines.append(f"• {line.name} ({line.sku}): {line.suggested_qty} und")
        msg_lines.append("")
        msg_lines.append("Gracias, quedamos atentos a disponibilidad y tiempo de entrega.")
        msg = "\n".join(msg_lines)
        suppliers_out.append(ReplenishSupplier(
            supplier_id=g["supplier_id"],
            supplier_name=g["supplier_name"],
            supplier_phone=g["supplier_phone"],
            lines=lines,
            total_units=total_units,
            total_cost=total_cost,
            whatsapp_url=_wa_link(g["supplier_phone"], msg),
        ))
    suppliers_out.sort(key=lambda x: -x.total_cost)

    return ReplenishmentOut(
        generated_at=now.isoformat(),
        target_days=target_days,
        total_cost=round(grand_total, 2),
        suppliers=suppliers_out,
    )


# ═══════════════════════════════════════════════════════════════
#  P3 — FIDELIZACIÓN POR MASCOTA (cumpleaños + desparasitación)
# ═══════════════════════════════════════════════════════════════
class PetReminder(BaseModel):
    customer_id: str
    customer_name: str
    phone: str | None
    pet_name: str | None
    pet_type: str | None
    reason: str           # "cumple" | "desparasitacion" | "vacuna"
    detail: str
    whatsapp_url: str | None = None


class PetCareOut(BaseModel):
    generated_at: str
    summary: dict
    birthdays: list[PetReminder]
    deworming_due: list[PetReminder]


def _parse_date(val) -> date | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val)[:10]).date()
    except (ValueError, TypeError):
        return None


@router.get(
    "/pet-care",
    response_model=PetCareOut,
    dependencies=[Depends(require_permission("crm:read"))],
)
async def pet_care(
    db: DBSession,
    deworming_interval_days: int = Query(90, ge=30, le=365),
) -> PetCareOut:
    today = datetime.now(UTC).date()

    rows = (
        await db.execute(
            select(Customer)
            .where(Customer.deleted_at == None)  # noqa: E711
        )
    ).scalars().all()

    birthdays: list[PetReminder] = []
    deworming: list[PetReminder] = []

    for c in rows:
        extra = c.extra or {}
        pet_name = extra.get("pet_name")
        pet_type = extra.get("pet_type")
        if not pet_name and not extra.get("pet_birthday") and not extra.get("last_deworming"):
            continue
        first_name = c.full_name.split(" ")[0] if c.full_name else "Hola"
        pet_label = pet_name or "tu mascota"

        # Cumpleaños este mes
        bday = _parse_date(extra.get("pet_birthday"))
        if bday is not None and bday.month == today.month:
            msg = (
                f"¡Hola {first_name}! 🎉🐾 Este mes {pet_label} está de cumpleaños. "
                f"En Bigotes y Paticas tenemos un regalito especial para celebrarlo. ¡Te esperamos!"
            )
            birthdays.append(PetReminder(
                customer_id=str(c.id),
                customer_name=c.full_name,
                phone=c.phone,
                pet_name=pet_name,
                pet_type=pet_type,
                reason="cumple",
                detail=f"Cumple el {bday.day}/{bday.month}",
                whatsapp_url=_wa_link(c.phone, msg),
            ))

        # Desparasitación / control
        last_dew = _parse_date(extra.get("last_deworming"))
        if last_dew is not None:
            days_since = (today - last_dew).days
            if days_since >= deworming_interval_days:
                msg = (
                    f"¡Hola {first_name}! 🐾 Ya pasaron {days_since} días desde la última "
                    f"desparasitación de {pet_label}. Es momento del refuerzo — tenemos el producto "
                    f"ideal y te lo llevamos a domicilio. ¿Lo reservamos?"
                )
                deworming.append(PetReminder(
                    customer_id=str(c.id),
                    customer_name=c.full_name,
                    phone=c.phone,
                    pet_name=pet_name,
                    pet_type=pet_type,
                    reason="desparasitacion",
                    detail=f"Última hace {days_since} días",
                    whatsapp_url=_wa_link(c.phone, msg),
                ))

    deworming.sort(key=lambda x: x.detail, reverse=True)

    return PetCareOut(
        generated_at=datetime.now(UTC).isoformat(),
        summary={
            "birthdays_this_month": len(birthdays),
            "deworming_due": len(deworming),
        },
        birthdays=birthdays[:100],
        deworming_due=deworming[:100],
    )
