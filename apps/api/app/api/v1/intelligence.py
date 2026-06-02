"""Centro de Inteligencia — recompra predictiva, retención y capital atrapado.

Pensado para crecer una tienda petshop: detectar a quién contactar HOY para
vender más (recompra de alimento), qué clientes valiosos se están enfriando, y
qué capital está atrapado en inventario sin rotación.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.deps import DBSession, require_permission
from app.models.catalog import Product
from app.models.crm import Customer
from app.models.inventory import Stock
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
