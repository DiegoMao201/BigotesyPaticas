"""Analytics / BI — endpoints completos para el panel ejecutivo."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, literal, select, text

from app.api.v1._date_ranges import mtd_ranges
from app.api.v1.intelligence import intelligence_overview
from app.deps import DBSession, require_permission
from app.models.catalog import Category, Product
from app.models.crm import Customer
from app.models.inventory import Stock
from app.models.ops import LegacyIdMap
from app.models.sales import Order, OrderItem, Payment

router = APIRouter(prefix="/analytics", tags=["analytics"])


class KpiOut(BaseModel):
    revenue_month: float
    revenue_prev_month: float
    revenue_delta_pct: float
    orders_month: int
    orders_prev_month: int
    orders_delta_pct: float
    avg_ticket: float
    low_stock_count: int


class ActionableKpis(BaseModel):
    gross_margin_pct: float
    gross_margin_prev_pct: float
    gross_margin_delta_pts: float
    repurchase_due: int
    repurchase_revenue_opportunity: float
    at_risk_count: int
    at_risk_value: float
    dead_stock_count: int
    trapped_capital: float
    below_cost_lines: int
    below_cost_loss: float
    new_customers_month: int
    new_customers_prev_month: int
    new_customers_delta_pct: float


class DailySale(BaseModel):
    date: str
    revenue: float
    orders: int


class TopProduct(BaseModel):
    product_id: str
    name: str
    sku: str
    units_sold: int
    revenue: float
    primary_image_url: str | None = None


class DashboardOut(BaseModel):
    kpis: KpiOut
    actionable: ActionableKpis
    daily_sales: list[DailySale]
    top_products: list[TopProduct]
    recent_orders: list[dict]


@router.get(
    "/dashboard",
    response_model=DashboardOut,
    dependencies=[Depends(require_permission("analytics:read"))],
)
async def get_dashboard(db: DBSession) -> DashboardOut:
    # Límites de mes en America/Bogota (no UTC crudo) — ver _date_ranges.py.
    # `now`/`start_month` acotan el mes actual (parcial); `end_prev` es el
    # mismo corte de día pero del mes anterior (MTD-vs-MTD real).
    start_month, now, start_prev, end_prev = mtd_ranges()

    # Revenue mes actual (MTD): [start_month, now] — "now" es un instante,
    # no un límite de día, por eso se incluye con <=.
    rev_month = (
        await db.execute(
            select(func.coalesce(func.sum(Order.grand_total), 0))
            .where(Order.occurred_at >= start_month)
            .where(Order.occurred_at <= now)
            .where(Order.status.notin_(["cancelled", "refunded"]))
        )
    ).scalar_one()

    # Revenue mismo corte del mes anterior: [start_prev, end_prev) — end_prev
    # es el inicio del día siguiente al corte, por eso el límite es <.
    rev_prev = (
        await db.execute(
            select(func.coalesce(func.sum(Order.grand_total), 0))
            .where(Order.occurred_at >= start_prev)
            .where(Order.occurred_at < end_prev)
            .where(Order.status.notin_(["cancelled", "refunded"]))
        )
    ).scalar_one()

    # Órdenes mes actual (MTD)
    ord_month = (
        await db.execute(
            select(func.count(Order.id))
            .where(Order.occurred_at >= start_month)
            .where(Order.occurred_at <= now)
            .where(Order.status.notin_(["cancelled"]))
        )
    ).scalar_one()

    # Órdenes mismo corte del mes anterior
    ord_prev = (
        await db.execute(
            select(func.count(Order.id))
            .where(Order.occurred_at >= start_prev)
            .where(Order.occurred_at < end_prev)
            .where(Order.status.notin_(["cancelled"]))
        )
    ).scalar_one()

    # COGS mes actual / mismo corte del mes anterior (mismo patrón que /bi)
    async def _cogs(start, end, inclusive_end: bool) -> float:
        q = (
            select(func.coalesce(func.sum(OrderItem.unit_cost * OrderItem.quantity), 0))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.occurred_at >= start)
            .where(Order.status.notin_(["cancelled", "refunded"]))
        )
        q = q.where(Order.occurred_at <= end) if inclusive_end else q.where(Order.occurred_at < end)
        return float((await db.execute(q)).scalar_one())

    cogs_month = await _cogs(start_month, now, inclusive_end=True)
    cogs_prev = await _cogs(start_prev, end_prev, inclusive_end=False)
    margin_month = (
        round((float(rev_month) - cogs_month) / float(rev_month) * 100, 1) if rev_month else 0.0
    )
    margin_prev = (
        round((float(rev_prev) - cogs_prev) / float(rev_prev) * 100, 1) if rev_prev else 0.0
    )

    # Ventas por debajo del costo, mes actual (líneas con margen negativo real)
    below_cost_lines, below_cost_loss = (
        await db.execute(
            select(
                func.count(OrderItem.id),
                func.coalesce(
                    func.sum((OrderItem.unit_cost - OrderItem.unit_price) * OrderItem.quantity), 0
                ),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.occurred_at >= start_month)
            .where(Order.occurred_at <= now)
            .where(Order.status.notin_(["cancelled", "refunded"]))
            .where(OrderItem.unit_price < OrderItem.unit_cost)
        )
    ).one()

    # Clientes nuevos MTD vs mismo corte del mes anterior (primera orden histórica)
    first_order_sub = (
        select(Order.customer_id, func.min(Order.occurred_at).label("first_at"))
        .where(Order.customer_id.isnot(None))
        .where(Order.status.notin_(["cancelled", "refunded"]))
        .group_by(Order.customer_id)
        .subquery()
    )
    new_customers_month = (
        await db.execute(
            select(func.count())
            .select_from(first_order_sub)
            .where(first_order_sub.c.first_at >= start_month, first_order_sub.c.first_at <= now)
        )
    ).scalar_one()
    new_customers_prev = (
        await db.execute(
            select(func.count())
            .select_from(first_order_sub)
            .where(first_order_sub.c.first_at >= start_prev, first_order_sub.c.first_at < end_prev)
        )
    ).scalar_one()

    # Recompra / riesgo de fuga / capital atrapado — reusa intelligence.py,
    # no se duplica la lógica. Se llama directo (no vía HTTP), por eso los
    # parámetros con default Query(...) se pasan explícitos como int.
    intel = await intelligence_overview(db, at_risk_days=60, dead_stock_days=90)

    # Stock bajo (< 5 unidades disponibles)
    low_stock = (
        await db.execute(
            select(func.count(func.distinct(Stock.product_id)))
            .where((Stock.quantity - Stock.reserved) < 5)
            .where((Stock.quantity - Stock.reserved) >= 0)
        )
    ).scalar_one()

    def _delta(curr, prev) -> float:
        if not prev:
            return 0.0
        return round((float(curr) - float(prev)) / float(prev) * 100, 1)

    avg_ticket = float(rev_month) / ord_month if ord_month else 0

    # Ventas diarias últimos 30 días
    since_30 = now - timedelta(days=30)
    day_trunc = func.date_trunc("day", Order.occurred_at)
    daily_rows = (
        await db.execute(
            select(
                day_trunc.label("day"),
                func.sum(Order.grand_total).label("revenue"),
                func.count(Order.id).label("orders"),
            )
            .where(Order.occurred_at >= since_30)
            .where(Order.status.notin_(["cancelled", "refunded"]))
            .group_by(day_trunc)
            .order_by(day_trunc)
        )
    ).all()

    daily_sales = [
        DailySale(
            date=r.day.strftime("%Y-%m-%d"),
            revenue=float(r.revenue or 0),
            orders=int(r.orders or 0),
        )
        for r in daily_rows
    ]

    # Top 5 productos por revenue este mes (subquery evita GroupingError en PG)
    valid_order_ids_sub = (
        select(Order.id)
        .where(Order.occurred_at >= start_month)
        .where(Order.status.notin_(["cancelled", "refunded"]))
    )
    top_rows = (
        await db.execute(
            select(
                OrderItem.product_id,
                OrderItem.name_snapshot,
                OrderItem.sku_snapshot,
                func.sum(OrderItem.quantity).label("units"),
                func.sum(OrderItem.unit_price * OrderItem.quantity - OrderItem.discount).label(
                    "rev"
                ),
            )
            .where(OrderItem.order_id.in_(valid_order_ids_sub))
            .group_by(OrderItem.product_id, OrderItem.name_snapshot, OrderItem.sku_snapshot)
            .order_by(
                func.sum(OrderItem.unit_price * OrderItem.quantity - OrderItem.discount).desc()
            )
            .limit(5)
        )
    ).all()

    top_products = [
        TopProduct(
            product_id=str(r.product_id),
            name=r.name_snapshot,
            sku=r.sku_snapshot,
            units_sold=int(r.units or 0),
            revenue=float(r.rev or 0),
        )
        for r in top_rows
    ]

    # Últimas 5 órdenes
    recent_rows = (
        (await db.execute(select(Order).order_by(Order.occurred_at.desc()).limit(5)))
        .scalars()
        .all()
    )

    recent_orders = [
        {
            "id": str(o.id),
            "order_number": o.order_number,
            "channel": o.channel,
            "status": o.status,
            "grand_total": float(o.grand_total),
            "payment_status": o.payment_status,
            "occurred_at": o.occurred_at.isoformat(),
        }
        for o in recent_rows
    ]

    return DashboardOut(
        kpis=KpiOut(
            revenue_month=float(rev_month),
            revenue_prev_month=float(rev_prev),
            revenue_delta_pct=_delta(rev_month, rev_prev),
            orders_month=int(ord_month),
            orders_prev_month=int(ord_prev),
            orders_delta_pct=_delta(ord_month, ord_prev),
            avg_ticket=avg_ticket,
            low_stock_count=int(low_stock),
        ),
        actionable=ActionableKpis(
            gross_margin_pct=margin_month,
            gross_margin_prev_pct=margin_prev,
            gross_margin_delta_pts=round(margin_month - margin_prev, 1),
            repurchase_due=intel.summary.repurchase_due,
            repurchase_revenue_opportunity=intel.summary.repurchase_revenue_opportunity,
            at_risk_count=intel.summary.at_risk_count,
            at_risk_value=intel.summary.at_risk_value,
            dead_stock_count=intel.summary.dead_stock_count,
            trapped_capital=intel.summary.trapped_capital,
            below_cost_lines=int(below_cost_lines or 0),
            below_cost_loss=float(below_cost_loss or 0),
            new_customers_month=int(new_customers_month or 0),
            new_customers_prev_month=int(new_customers_prev or 0),
            new_customers_delta_pct=_delta(new_customers_month, new_customers_prev),
        ),
        daily_sales=daily_sales,
        top_products=top_products,
        recent_orders=recent_orders,
    )


class StockAlertOut(BaseModel):
    product_id: str
    sku: str
    name: str
    available: int
    level: str  # "critical" | "low" | "ok"


@router.get(
    "/stock-alerts",
    response_model=list[StockAlertOut],
    dependencies=[Depends(require_permission("analytics:read"))],
)
async def stock_alerts(db: DBSession, threshold: int = 10) -> list[StockAlertOut]:
    rows = (
        await db.execute(
            select(
                Stock.product_id,
                Product.sku,
                Product.name,
                func.sum(Stock.quantity - Stock.reserved).label("available"),
            )
            .join(Product, Product.id == Stock.product_id)
            .where(Product.is_active == True)  # noqa: E712
            .where(Product.deleted_at == None)  # noqa: E711
            .group_by(Stock.product_id, Product.sku, Product.name)
            .having(func.sum(Stock.quantity - Stock.reserved) <= threshold)
            .order_by(func.sum(Stock.quantity - Stock.reserved))
            .limit(50)
        )
    ).all()
    return [
        StockAlertOut(
            product_id=str(r.product_id),
            sku=r.sku,
            name=r.name,
            available=int(r.available or 0),
            level="critical" if (r.available or 0) <= 0 else "low",
        )
        for r in rows
    ]


# ═══════════════════════════════════════════════════════════════
#  BI FULL — Un solo endpoint con TODO lo que necesita el panel
# ═══════════════════════════════════════════════════════════════


class ChannelBreakdown(BaseModel):
    channel: str
    revenue: float
    orders: int
    pct: float


class MethodBreakdown(BaseModel):
    method: str
    revenue: float
    orders: int
    pct: float


class MonthlyPoint(BaseModel):
    year_month: str
    revenue: float
    orders: int
    avg_ticket: float


class TopCustomer(BaseModel):
    customer_id: str | None
    name: str
    orders: int
    revenue: float
    last_purchase: str | None


class CategoryRevenue(BaseModel):
    category: str
    revenue: float
    units: int
    pct: float


class HeatmapCell(BaseModel):
    weekday: int  # 0=Lun, 6=Dom
    hour: int
    orders: int


class PnLRow(BaseModel):
    label: str
    value: float
    pct: float | None = None


class BiFull(BaseModel):
    period_start: str
    period_end: str
    # KPIs resumen
    revenue_total: float
    orders_total: int
    avg_ticket: float
    gross_margin_pct: float
    # Desgloses
    by_channel: list[ChannelBreakdown]
    by_method: list[MethodBreakdown]
    monthly_trend: list[MonthlyPoint]
    top_customers: list[TopCustomer]
    by_category: list[CategoryRevenue]
    heatmap: list[HeatmapCell]
    # P&L
    revenue: float
    cogs: float
    gross_profit: float
    expenses_total: float
    net_profit: float
    expenses_by_category: list[dict]


@router.get(
    "/bi",
    response_model=BiFull,
    dependencies=[Depends(require_permission("analytics:read"))],
)
async def get_bi_full(
    db: DBSession,
    days: int = Query(90, ge=7, le=730),
) -> BiFull:
    now = datetime.now(UTC)
    since = now - timedelta(days=days)

    # ── Revenue & orders totals ────────────────────────────────
    rev_total, ord_total = (
        await db.execute(
            select(
                func.coalesce(func.sum(Order.grand_total), 0),
                func.count(Order.id),
            )
            .where(Order.occurred_at >= since)
            .where(Order.status.notin_(["cancelled", "refunded"]))
        )
    ).one()
    rev_total = float(rev_total or 0)
    ord_total = int(ord_total or 0)
    avg_ticket = rev_total / ord_total if ord_total else 0

    # ── COGS (stock cost x qty from order items) ───────────────
    cogs_result = (
        await db.execute(
            select(func.coalesce(func.sum(OrderItem.unit_cost * OrderItem.quantity), 0))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.occurred_at >= since)
            .where(Order.status.notin_(["cancelled", "refunded"]))
        )
    ).scalar_one()
    cogs = float(cogs_result or 0)
    gross_profit = rev_total - cogs
    gross_margin_pct = round(gross_profit / rev_total * 100, 1) if rev_total > 0 else 0

    # ── By channel ─────────────────────────────────────────────
    ch_rows = (
        await db.execute(
            select(
                Order.channel,
                func.sum(Order.grand_total).label("rev"),
                func.count(Order.id).label("cnt"),
            )
            .where(Order.occurred_at >= since)
            .where(Order.status.notin_(["cancelled", "refunded"]))
            .group_by(Order.channel)
            .order_by(func.sum(Order.grand_total).desc())
        )
    ).all()
    by_channel = [
        ChannelBreakdown(
            channel=r.channel,
            revenue=float(r.rev or 0),
            orders=int(r.cnt or 0),
            pct=round(float(r.rev or 0) / rev_total * 100, 1) if rev_total else 0,
        )
        for r in ch_rows
    ]

    # ── By payment method ──────────────────────────────────────
    pm_rows = (
        await db.execute(
            select(
                func.coalesce(Order.payment_method, Payment.method, literal("Sin método")).label(
                    "meth"
                ),
                func.sum(Order.grand_total).label("rev"),
                func.count(func.distinct(Order.id)).label("cnt"),
            )
            .outerjoin(Payment, Payment.order_id == Order.id)
            .where(Order.occurred_at >= since)
            .where(Order.status.notin_(["cancelled", "refunded"]))
            .group_by(text("1"))
            .order_by(func.sum(Order.grand_total).desc())
        )
    ).all()
    by_method = [
        MethodBreakdown(
            method=str(r.meth or "Desconocido"),
            revenue=float(r.rev or 0),
            orders=int(r.cnt or 0),
            pct=round(float(r.rev or 0) / rev_total * 100, 1) if rev_total else 0,
        )
        for r in pm_rows
    ]

    # ── Monthly trend ──────────────────────────────────────────
    month_trunc = func.date_trunc("month", Order.occurred_at)
    mo_rows = (
        await db.execute(
            select(
                month_trunc.label("mo"),
                func.sum(Order.grand_total).label("rev"),
                func.count(Order.id).label("cnt"),
            )
            .where(Order.occurred_at >= now - timedelta(days=365))
            .where(Order.status.notin_(["cancelled", "refunded"]))
            .group_by(month_trunc)
            .order_by(month_trunc)
        )
    ).all()
    monthly_trend = [
        MonthlyPoint(
            year_month=r.mo.strftime("%Y-%m"),
            revenue=float(r.rev or 0),
            orders=int(r.cnt or 0),
            avg_ticket=round(float(r.rev or 0) / int(r.cnt or 1), 0),
        )
        for r in mo_rows
    ]

    # ── Top customers ──────────────────────────────────────────
    top_cust_rows = (
        await db.execute(
            select(
                Order.customer_id,
                func.coalesce(
                    Customer.full_name,
                    func.coalesce(text("metadata->>'cliente_nombre'"), literal("Anónimo")),
                ).label("cname"),
                func.count(Order.id).label("cnt"),
                func.sum(Order.grand_total).label("rev"),
                func.max(Order.occurred_at).label("last"),
            )
            .outerjoin(Customer, Customer.id == Order.customer_id)
            .where(Order.occurred_at >= since)
            .where(Order.status.notin_(["cancelled", "refunded"]))
            .group_by(Order.customer_id, text("2"))
            .order_by(func.sum(Order.grand_total).desc())
            .limit(15)
        )
    ).all()
    top_customers = [
        TopCustomer(
            customer_id=str(r.customer_id) if r.customer_id else None,
            name=str(r.cname or "Anónimo"),
            orders=int(r.cnt or 0),
            revenue=float(r.rev or 0),
            last_purchase=r.last.isoformat() if r.last else None,
        )
        for r in top_cust_rows
    ]

    # ── By category ────────────────────────────────────────────
    cat_rows = (
        await db.execute(
            select(
                func.coalesce(Category.name, literal("Sin categoría")).label("cat"),
                func.sum(OrderItem.unit_price * OrderItem.quantity - OrderItem.discount).label(
                    "rev"
                ),
                func.sum(OrderItem.quantity).label("units"),
            )
            .select_from(OrderItem)
            .join(Order, Order.id == OrderItem.order_id)
            .outerjoin(Product, Product.id == OrderItem.product_id)
            .outerjoin(Category, Category.id == Product.category_id)
            .where(Order.occurred_at >= since)
            .where(Order.status.notin_(["cancelled", "refunded"]))
            .group_by(text("1"))
            .order_by(
                func.sum(OrderItem.unit_price * OrderItem.quantity - OrderItem.discount).desc()
            )
            .limit(20)
        )
    ).all()
    cat_total_rev = sum(float(r.rev or 0) for r in cat_rows) or 1
    by_category = [
        CategoryRevenue(
            category=str(r.cat),
            revenue=float(r.rev or 0),
            units=int(r.units or 0),
            pct=round(float(r.rev or 0) / cat_total_rev * 100, 1),
        )
        for r in cat_rows
    ]

    # ── Heatmap day x hour ─────────────────────────────────────
    # Extract weekday (0=Sun PG style) and hour from occurred_at
    hm_rows = (
        await db.execute(
            select(
                func.extract("dow", Order.occurred_at).label("wd"),
                func.extract("hour", Order.occurred_at).label("hr"),
                func.count(Order.id).label("cnt"),
            )
            .where(Order.occurred_at >= since)
            .where(Order.status.notin_(["cancelled", "refunded"]))
            .group_by(text("1, 2"))
            .order_by(text("1, 2"))
        )
    ).all()
    heatmap = [
        HeatmapCell(
            weekday=int(r.wd) % 7,
            hour=int(r.hr),
            orders=int(r.cnt),
        )
        for r in hm_rows
    ]

    # ── Expenses (P&L) ─────────────────────────────────────────
    expense_rows = (
        (await db.execute(select(LegacyIdMap).where(LegacyIdMap.entity == "gasto"))).scalars().all()
    )

    expenses_total = 0.0
    cat_exp: dict[str, float] = {}
    for r in expense_rows:
        e = r.extra or {}
        f = str(e.get("fecha", ""))
        try:
            fd = datetime.fromisoformat(f[:10]) if f else None
        except Exception:
            fd = None
        if fd and fd.replace(tzinfo=UTC) >= since:
            m = float(e.get("monto") or 0)
            expenses_total += m
            c = str(e.get("categoria", "Otros"))
            cat_exp[c] = cat_exp.get(c, 0) + m

    expenses_by_category = sorted(
        [{"category": k, "total": v} for k, v in cat_exp.items()],
        key=lambda x: x["total"],
        reverse=True,
    )
    net_profit = gross_profit - expenses_total

    return BiFull(
        period_start=since.strftime("%Y-%m-%d"),
        period_end=now.strftime("%Y-%m-%d"),
        revenue_total=rev_total,
        orders_total=ord_total,
        avg_ticket=avg_ticket,
        gross_margin_pct=gross_margin_pct,
        by_channel=by_channel,
        by_method=by_method,
        monthly_trend=monthly_trend,
        top_customers=top_customers,
        by_category=by_category,
        heatmap=heatmap,
        revenue=rev_total,
        cogs=cogs,
        gross_profit=gross_profit,
        expenses_total=expenses_total,
        net_profit=net_profit,
        expenses_by_category=expenses_by_category,
    )


# ── Sales detail with period comparison ───────────────────────────


class SalesPeriodComparison(BaseModel):
    current_revenue: float
    prev_revenue: float
    delta_pct: float
    current_orders: int
    prev_orders: int
    daily_current: list[DailySale]
    daily_prev: list[DailySale]


@router.get(
    "/sales-comparison",
    response_model=SalesPeriodComparison,
    dependencies=[Depends(require_permission("analytics:read"))],
)
async def sales_comparison(
    db: DBSession,
    days: int = Query(30, ge=7, le=180),
) -> SalesPeriodComparison:
    now = datetime.now(UTC)
    since = now - timedelta(days=days)
    prev_since = since - timedelta(days=days)

    def _q(start, end):
        return (
            select(
                func.coalesce(func.sum(Order.grand_total), 0),
                func.count(Order.id),
            )
            .where(Order.occurred_at >= start)
            .where(Order.occurred_at < end)
            .where(Order.status.notin_(["cancelled", "refunded"]))
        )

    cur_rev, cur_ord = (await db.execute(_q(since, now))).one()
    prev_rev, prev_ord = (await db.execute(_q(prev_since, since))).one()

    def _delta(c, p):
        return round((float(c) - float(p)) / float(p) * 100, 1) if p else 0.0

    day_trunc = func.date_trunc("day", Order.occurred_at)

    def _daily(start, end):
        return (
            select(
                day_trunc.label("d"),
                func.sum(Order.grand_total).label("rev"),
                func.count(Order.id).label("cnt"),
            )
            .where(Order.occurred_at >= start)
            .where(Order.occurred_at < end)
            .where(Order.status.notin_(["cancelled", "refunded"]))
            .group_by(day_trunc)
            .order_by(day_trunc)
        )

    curr_rows = (await db.execute(_daily(since, now))).all()
    prev_rows = (await db.execute(_daily(prev_since, since))).all()

    return SalesPeriodComparison(
        current_revenue=float(cur_rev or 0),
        prev_revenue=float(prev_rev or 0),
        delta_pct=_delta(cur_rev, prev_rev),
        current_orders=int(cur_ord or 0),
        prev_orders=int(prev_ord or 0),
        daily_current=[
            DailySale(
                date=r.d.strftime("%Y-%m-%d"), revenue=float(r.rev or 0), orders=int(r.cnt or 0)
            )
            for r in curr_rows
        ],
        daily_prev=[
            DailySale(
                date=r.d.strftime("%Y-%m-%d"), revenue=float(r.rev or 0), orders=int(r.cnt or 0)
            )
            for r in prev_rows
        ],
    )
