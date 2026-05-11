"""Analytics / dashboard stats — endpoint para el panel ejecutivo."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from app.deps import DBSession, require_permission
from app.models.catalog import Product
from app.models.crm import Customer
from app.models.inventory import Stock
from app.models.sales import Order, OrderItem

router = APIRouter(prefix="/analytics", tags=["analytics"])


class KpiOut(BaseModel):
    revenue_month: float
    revenue_prev_month: float
    revenue_delta_pct: float
    orders_month: int
    orders_prev_month: int
    orders_delta_pct: float
    avg_ticket: float
    products_active: int
    customers_total: int
    low_stock_count: int


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
    daily_sales: list[DailySale]
    top_products: list[TopProduct]
    recent_orders: list[dict]


@router.get(
    "/dashboard",
    response_model=DashboardOut,
    dependencies=[Depends(require_permission("analytics:read"))],
)
async def get_dashboard(db: DBSession) -> DashboardOut:
    now = datetime.now(UTC)
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_prev = (start_month - timedelta(days=1)).replace(day=1)
    end_prev = start_month

    # Revenue mes actual
    rev_month = (
        await db.execute(
            select(func.coalesce(func.sum(Order.grand_total), 0))
            .where(Order.occurred_at >= start_month)
            .where(Order.status.notin_(["cancelled", "refunded"]))
        )
    ).scalar_one()

    # Revenue mes anterior
    rev_prev = (
        await db.execute(
            select(func.coalesce(func.sum(Order.grand_total), 0))
            .where(Order.occurred_at >= start_prev)
            .where(Order.occurred_at < end_prev)
            .where(Order.status.notin_(["cancelled", "refunded"]))
        )
    ).scalar_one()

    # Órdenes mes actual
    ord_month = (
        await db.execute(
            select(func.count(Order.id))
            .where(Order.occurred_at >= start_month)
            .where(Order.status.notin_(["cancelled"]))
        )
    ).scalar_one()

    # Órdenes mes anterior
    ord_prev = (
        await db.execute(
            select(func.count(Order.id))
            .where(Order.occurred_at >= start_prev)
            .where(Order.occurred_at < end_prev)
            .where(Order.status.notin_(["cancelled"]))
        )
    ).scalar_one()

    # Productos activos
    prod_active = (
        await db.execute(
            select(func.count(Product.id))
            .where(Product.is_active == True)  # noqa: E712
            .where(Product.deleted_at == None)  # noqa: E711
        )
    ).scalar_one()

    # Clientes total
    cust_total = (
        await db.execute(
            select(func.count(Customer.id)).where(Customer.deleted_at == None)  # noqa: E711
        )
    ).scalar_one()

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
    daily_rows = (
        await db.execute(
            select(
                func.date_trunc("day", Order.occurred_at).label("day"),
                func.sum(Order.grand_total).label("revenue"),
                func.count(Order.id).label("orders"),
            )
            .where(Order.occurred_at >= since_30)
            .where(Order.status.notin_(["cancelled", "refunded"]))
            .group_by(func.date_trunc("day", Order.occurred_at))
            .order_by(func.date_trunc("day", Order.occurred_at))
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

    # Top 5 productos por revenue este mes
    top_rows = (
        await db.execute(
            select(
                OrderItem.product_id,
                OrderItem.name_snapshot,
                OrderItem.sku_snapshot,
                func.sum(OrderItem.quantity).label("units"),
                func.sum(OrderItem.unit_price * OrderItem.quantity - OrderItem.discount).label("rev"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.occurred_at >= start_month)
            .where(Order.status.notin_(["cancelled", "refunded"]))
            .group_by(OrderItem.product_id, OrderItem.name_snapshot, OrderItem.sku_snapshot)
            .order_by(func.sum(OrderItem.unit_price * OrderItem.quantity - OrderItem.discount).desc())
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
        await db.execute(
            select(Order)
            .order_by(Order.occurred_at.desc())
            .limit(5)
        )
    ).scalars().all()

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
            products_active=int(prod_active),
            customers_total=int(cust_total),
            low_stock_count=int(low_stock),
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
