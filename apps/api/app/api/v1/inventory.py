"""Endpoints de inventario: stock por SKU/producto, ajustes."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.deps import CurrentUser, DBSession, require_permission
from app.models.catalog import Product
from app.models.inventory import Stock, StockLocation, StockMovement

router = APIRouter(prefix="/inventory", tags=["inventory"])


class StockOut(BaseModel):
    product_id: uuid.UUID
    location_id: uuid.UUID
    quantity: int
    reserved: int
    available: int


class AdjustmentIn(BaseModel):
    product_id: uuid.UUID
    location_id: uuid.UUID | None = None
    quantity_delta: int = Field(description="Positivo o negativo")
    notes: str | None = None


@router.get("/stock/{product_id}", response_model=list[StockOut])
async def get_stock(product_id: uuid.UUID, db: DBSession):
    rows = (
        await db.execute(select(Stock).where(Stock.product_id == product_id))
    ).scalars().all()
    return [
        StockOut(
            product_id=s.product_id,
            location_id=s.location_id,
            quantity=s.quantity,
            reserved=s.reserved,
            available=max(0, s.quantity - s.reserved),
        )
        for s in rows
    ]


@router.post(
    "/adjust",
    response_model=StockOut,
    dependencies=[Depends(require_permission("inventory:adjust"))],
)
async def adjust_stock(payload: AdjustmentIn, db: DBSession, user: CurrentUser):
    # Resolver location default si no se da
    location_id = payload.location_id
    if location_id is None:
        loc = (
            await db.execute(
                select(StockLocation).where(StockLocation.is_default == 1).limit(1)
            )
        ).scalar_one_or_none()
        if loc is None:
            raise HTTPException(
                status_code=400, detail="No hay location default configurada"
            )
        location_id = loc.id

    # Lock pesimista sobre la fila de stock
    stock = (
        await db.execute(
            select(Stock)
            .where(Stock.product_id == payload.product_id)
            .where(Stock.location_id == location_id)
            .with_for_update()
        )
    ).scalar_one_or_none()

    if stock is None:
        if payload.quantity_delta < 0:
            raise HTTPException(status_code=400, detail="Sin stock para descontar")
        stock = Stock(
            product_id=payload.product_id,
            location_id=location_id,
            quantity=0,
        )
        db.add(stock)

    new_qty = stock.quantity + payload.quantity_delta
    if new_qty < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stock insuficiente: actual={stock.quantity}, delta={payload.quantity_delta}",
        )
    stock.quantity = new_qty

    movement = StockMovement(
        product_id=payload.product_id,
        location_id=location_id,
        movement_type="ADJUSTMENT",
        quantity_delta=payload.quantity_delta,
        quantity_after=new_qty,
        notes=payload.notes,
        occurred_at=datetime.now(UTC),
        created_by=user.email,
    )
    db.add(movement)
    await db.commit()
    await db.refresh(stock)

    return StockOut(
        product_id=stock.product_id,
        location_id=stock.location_id,
        quantity=stock.quantity,
        reserved=stock.reserved,
        available=max(0, stock.quantity - stock.reserved),
    )


class BatchAdjustmentItem(BaseModel):
    product_id: uuid.UUID
    quantity_delta: int = Field(description="Positivo o negativo, distinto de 0")
    notes: str | None = None


class BatchAdjustmentIn(BaseModel):
    location_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, description="Nota común para todo el lote")
    items: list[BatchAdjustmentItem] = Field(min_length=1)


class BatchAdjustmentResultItem(BaseModel):
    product_id: uuid.UUID
    quantity_delta: int
    quantity_after: int


class BatchAdjustmentOut(BaseModel):
    applied: int
    total_delta: int
    items: list[BatchAdjustmentResultItem]


@router.post(
    "/adjust/batch",
    response_model=BatchAdjustmentOut,
    dependencies=[Depends(require_permission("inventory:adjust"))],
)
async def adjust_stock_batch(payload: BatchAdjustmentIn, db: DBSession, user: CurrentUser):
    """Aplica varios ajustes de stock en una sola transacción (atómico).

    Si algún producto queda con stock negativo, se revierte TODO el lote.
    """
    # Resolver location default una sola vez
    location_id = payload.location_id
    if location_id is None:
        loc = (
            await db.execute(
                select(StockLocation).where(StockLocation.is_default == 1).limit(1)
            )
        ).scalar_one_or_none()
        if loc is None:
            raise HTTPException(status_code=400, detail="No hay location default configurada")
        location_id = loc.id

    # Validar que no se repita el mismo producto en el lote
    seen: set[uuid.UUID] = set()
    for it in payload.items:
        if it.quantity_delta == 0:
            raise HTTPException(status_code=400, detail="Hay un ajuste con cantidad 0")
        if it.product_id in seen:
            raise HTTPException(
                status_code=400,
                detail=f"Producto repetido en el lote: {it.product_id}",
            )
        seen.add(it.product_id)

    results: list[BatchAdjustmentResultItem] = []
    total_delta = 0
    now = datetime.now(UTC)

    for it in payload.items:
        stock = (
            await db.execute(
                select(Stock)
                .where(Stock.product_id == it.product_id)
                .where(Stock.location_id == location_id)
                .with_for_update()
            )
        ).scalar_one_or_none()

        if stock is None:
            if it.quantity_delta < 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Sin stock para descontar en producto {it.product_id}",
                )
            stock = Stock(product_id=it.product_id, location_id=location_id, quantity=0)
            db.add(stock)

        new_qty = stock.quantity + it.quantity_delta
        if new_qty < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Stock insuficiente en {it.product_id}: "
                    f"actual={stock.quantity}, delta={it.quantity_delta}"
                ),
            )
        stock.quantity = new_qty
        total_delta += it.quantity_delta

        db.add(StockMovement(
            product_id=it.product_id,
            location_id=location_id,
            movement_type="ADJUSTMENT",
            quantity_delta=it.quantity_delta,
            quantity_after=new_qty,
            notes=it.notes or payload.notes,
            occurred_at=now,
            created_by=user.email,
        ))
        results.append(BatchAdjustmentResultItem(
            product_id=it.product_id,
            quantity_delta=it.quantity_delta,
            quantity_after=new_qty,
        ))

    await db.commit()
    return BatchAdjustmentOut(applied=len(results), total_delta=total_delta, items=results)


# ─────────────── List all stock with product info (for inventory page) ────────────

class StockRowOut(BaseModel):
    product_id: uuid.UUID
    sku: str
    name: str
    category_name: str | None = None
    quantity: int
    reserved: int
    available: int
    cost: float
    price: float
    margin_pct: float
    stock_value_cost: float
    stock_value_price: float


class StockListResponse(BaseModel):
    items: list[StockRowOut]
    total: int
    page: int
    page_size: int
    total_value_cost: float
    total_value_price: float
    out_of_stock: int
    low_stock: int


@router.get("/stock", response_model=StockListResponse)
async def list_stock(
    db: DBSession,
    user: CurrentUser,
    q: str | None = Query(None),
    only_in_stock: bool = False,
    only_low_stock: bool = False,
    sort_by: str = Query("quantity", pattern="^(quantity|cost|price|stock_value_cost|stock_value_price|margin_pct|name|sku)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    # Sum stock per product
    stock_sub = (
        select(
            Stock.product_id.label("product_id"),
            func.coalesce(func.sum(Stock.quantity), 0).label("qty"),
            func.coalesce(func.sum(Stock.reserved), 0).label("reserved"),
        )
        .group_by(Stock.product_id)
        .subquery()
    )

    stmt = (
        select(Product, stock_sub.c.qty, stock_sub.c.reserved)
        .outerjoin(stock_sub, stock_sub.c.product_id == Product.id)
        .where(Product.deleted_at.is_(None))
    )
    if q:
        # Multi-token AND: each word must appear in name or sku (order-independent)
        for token in q.split():
            like = f"%{token}%"
            stmt = stmt.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))

    rows = (await db.execute(stmt)).all()
    items = []
    total_value_cost = 0.0
    total_value_price = 0.0
    out_of_stock = 0
    low_stock = 0
    for p, qty, reserved in rows:
        q_int = int(qty or 0)
        r_int = int(reserved or 0)
        avail = max(0, q_int - r_int)
        cost = float(p.cost or 0)
        price = float(p.price or 0)
        if only_in_stock and q_int <= 0:
            continue
        if only_low_stock and q_int > 5:
            continue
        if q_int <= 0:
            out_of_stock += 1
        elif q_int < 5:
            low_stock += 1
        sv_cost = q_int * cost
        sv_price = q_int * price
        margin = round((price - cost) / price * 100, 1) if price > 0 else 0.0
        total_value_cost += sv_cost
        total_value_price += sv_price
        items.append(StockRowOut(
            product_id=p.id,
            sku=p.sku,
            name=p.name,
            category_name=None,
            quantity=q_int,
            reserved=r_int,
            available=avail,
            cost=cost,
            price=price,
            margin_pct=margin,
            stock_value_cost=sv_cost,
            stock_value_price=sv_price,
        ))

    # Sort
    reverse = (sort_dir == "desc")
    sort_key_map = {
        "quantity": lambda x: x.quantity,
        "cost": lambda x: x.cost,
        "price": lambda x: x.price,
        "stock_value_cost": lambda x: x.stock_value_cost,
        "stock_value_price": lambda x: x.stock_value_price,
        "margin_pct": lambda x: x.margin_pct,
        "name": lambda x: x.name.lower(),
        "sku": lambda x: x.sku.lower(),
    }
    items.sort(key=sort_key_map.get(sort_by, lambda x: -x.quantity), reverse=reverse)
    total = len(items)
    start_idx = (page - 1) * page_size
    return StockListResponse(
        items=items[start_idx:start_idx + page_size],
        total=total,
        page=page,
        page_size=page_size,
        total_value_cost=total_value_cost,
        total_value_price=total_value_price,
        out_of_stock=out_of_stock,
        low_stock=low_stock,
    )


# ─────────────── List stock movements ────────────────────

class MovementOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str | None = None
    product_sku: str | None = None
    movement_type: str
    quantity_delta: int
    quantity_after: int
    unit_cost: float | None = None
    reference_type: str | None = None
    reference_id: str | None = None
    notes: str | None = None
    occurred_at: datetime
    created_by: str | None = None


@router.get("/movements", response_model=dict)
async def list_movements(
    db: DBSession,
    user: CurrentUser,
    product_id: uuid.UUID | None = None,
    movement_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    stmt = select(StockMovement, Product.name, Product.sku).join(
        Product, Product.id == StockMovement.product_id
    )
    if product_id:
        stmt = stmt.where(StockMovement.product_id == product_id)
    if movement_type:
        stmt = stmt.where(StockMovement.movement_type == movement_type)
    stmt = stmt.order_by(StockMovement.occurred_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).all()
    items = [
        MovementOut(
            id=m.id,
            product_id=m.product_id,
            product_name=name,
            product_sku=sku,
            movement_type=m.movement_type,
            quantity_delta=m.quantity_delta,
            quantity_after=m.quantity_after,
            unit_cost=float(m.unit_cost) if m.unit_cost is not None else None,
            reference_type=m.reference_type,
            reference_id=str(m.reference_id) if m.reference_id else None,
            notes=m.notes,
            occurred_at=m.occurred_at,
            created_by=m.created_by,
        )
        for m, name, sku in rows
    ]
    return {"items": items, "total": len(items)}


# ─────────────── Update product pricing (cost + price) ────────────

class PricingUpdateIn(BaseModel):
    cost: float | None = Field(None, ge=0, description="Costo unitario (precio de compra)")
    price: float | None = Field(None, ge=0, description="Precio de venta público")


class PricingUpdateOut(BaseModel):
    product_id: uuid.UUID
    sku: str
    name: str
    cost: float
    price: float
    margin_pct: float


@router.patch(
    "/stock/{product_id}/pricing",
    response_model=PricingUpdateOut,
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def update_product_pricing(
    product_id: uuid.UUID,
    payload: PricingUpdateIn,
    db: DBSession,
    user: CurrentUser,
):
    """Actualiza costo y/o precio de venta de un producto."""
    product = (
        await db.execute(
            select(Product).where(Product.id == product_id).where(Product.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if payload.cost is not None:
        from decimal import Decimal
        product.cost = Decimal(str(payload.cost))
    if payload.price is not None:
        from decimal import Decimal
        product.price = Decimal(str(payload.price))

    await db.commit()
    await db.refresh(product)

    cost = float(product.cost or 0)
    price = float(product.price or 0)
    margin = round((price - cost) / price * 100, 1) if price > 0 else 0.0

    return PricingUpdateOut(
        product_id=product.id,
        sku=product.sku,
        name=product.name,
        cost=cost,
        price=price,
        margin_pct=margin,
    )


# ─── Analytics: movements per product, ABC, reorder suggestions ───

@router.get("/movements/by-product/{product_id}")
async def product_movements(
    product_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
    days: int = Query(30, ge=1, le=365),
):
    """Movimientos de stock de un producto en los últimos N días."""
    from datetime import timedelta
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = (await db.execute(
        select(StockMovement)
        .where(StockMovement.product_id == product_id, StockMovement.occurred_at >= cutoff)
        .order_by(StockMovement.occurred_at.desc())
        .limit(500)
    )).scalars().all()
    return {
        "product_id": str(product_id),
        "days": days,
        "movements": [
            {
                "id": str(m.id),
                "type": m.movement_type,
                "quantity": m.quantity_delta,
                "occurred_at": m.occurred_at.isoformat(),
                "reference": m.reference_type,
                "notes": m.notes,
            } for m in rows
        ],
    }


@router.get("/analytics/velocity")
async def velocity_analysis(
    db: DBSession,
    user: CurrentUser,
    days_short: int = Query(30, ge=7, le=90),
    days_long: int = Query(90, ge=30, le=365),
):
    """Velocidad de venta blended (65% largo + 35% corto) con ABC y reorder.

    Lógica portada de Inventario_Nexus.py — Streamlit (heurística pet-shop).
    """
    from datetime import timedelta
    from sqlalchemy import text

    cutoff_short = datetime.now(UTC) - timedelta(days=days_short)
    cutoff_long = datetime.now(UTC) - timedelta(days=days_long)

    # SALE movements (negative qty) por producto
    short_q = await db.execute(text("""
        SELECT product_id::text, SUM(ABS(quantity_delta)) AS units
        FROM inventory.stock_movements
        WHERE movement_type = 'SALE' AND occurred_at >= :cutoff
        GROUP BY product_id
    """), {"cutoff": cutoff_short})
    short_map = {r[0]: float(r[1] or 0) for r in short_q.all()}

    long_q = await db.execute(text("""
        SELECT product_id::text, SUM(ABS(quantity_delta)) AS units
        FROM inventory.stock_movements
        WHERE movement_type = 'SALE' AND occurred_at >= :cutoff
        GROUP BY product_id
    """), {"cutoff": cutoff_long})
    long_map = {r[0]: float(r[1] or 0) for r in long_q.all()}

    # Productos + stock + costo + precio
    rows = await db.execute(text("""
        WITH latest_supplier AS (
            SELECT DISTINCT ON (m.product_id)
                   m.product_id,
                   s.id AS supplier_id,
                   s.name AS supplier_name
            FROM purchasing.supplier_sku_map m
            JOIN purchasing.suppliers s ON s.id = m.supplier_id
            WHERE s.is_active = true
            ORDER BY m.product_id, m.last_seen_at DESC NULLS LAST, m.created_at DESC
        )
        SELECT p.id::text,
               p.sku,
               p.name,
               p.cost::float,
               p.price::float,
               c.name AS category_name,
               ls.supplier_id::text,
               ls.supplier_name,
               COALESCE(SUM(s.quantity - s.reserved), 0) AS stock
        FROM catalog.products p
        LEFT JOIN catalog.categories c ON c.id = p.category_id
        LEFT JOIN latest_supplier ls ON ls.product_id = p.id
        LEFT JOIN inventory.stock s ON s.product_id = p.id
        WHERE p.deleted_at IS NULL AND p.is_active = true
        GROUP BY p.id, c.name, ls.supplier_id, ls.supplier_name
    """))

    productos = []
    for r in rows.all():
        pid, sku, name, cost, price, category_name, supplier_id, supplier_name, stock = r
        v_short = short_map.get(pid, 0)
        v_long = long_map.get(pid, 0)
        vel_short = v_short / days_short
        vel_long = v_long / days_long
        vel_blend = 0.65 * vel_long + 0.35 * vel_short
        # Confidence damping (poca historia → menos confianza)
        conf = min(1.0, v_long / 6.0)
        velocidad = vel_blend * conf

        DIAS_OBJETIVO = 8
        DIAS_SEGURIDAD = 1
        LEAD_TIME = 5
        stock_seguridad = velocidad * DIAS_SEGURIDAD
        punto_reorden = velocidad * LEAD_TIME + stock_seguridad
        stock_objetivo = velocidad * DIAS_OBJETIVO + stock_seguridad
        faltante = max(0, stock_objetivo - (stock or 0))

        # Estado
        if stock <= 0:
            estado = "AGOTADO"
        elif velocidad > 0 and stock <= punto_reorden:
            estado = "COMPRAR"
        elif velocidad > 0 and stock > velocidad * 120:
            estado = "SOBRESTOCK"
        else:
            estado = "OK"

        valor_ventas_long = v_long * (price or 0)
        dias_cobertura = (stock / velocidad) if velocidad > 0 else 9999

        productos.append({
            "product_id": pid,
            "sku": sku,
            "name": name,
            "category_name": category_name,
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "stock": int(stock or 0),
            "cost": cost or 0,
            "price": price or 0,
            "v_short": v_short,
            "v_long": v_long,
            "velocidad_diaria": round(velocidad, 3),
            "punto_reorden": round(punto_reorden, 1),
            "stock_objetivo": round(stock_objetivo, 1),
            "faltante": round(faltante, 1),
            "dias_cobertura": round(dias_cobertura, 1) if dias_cobertura < 9999 else None,
            "valor_ventas_long": round(valor_ventas_long, 0),
            "estado": estado,
            "requiere_compra": estado in ("AGOTADO", "COMPRAR"),
        })

    # ABC analysis: cumulative Pareto sobre valor_ventas_long
    productos.sort(key=lambda x: -x["valor_ventas_long"])
    total_val = sum(p["valor_ventas_long"] for p in productos) or 1
    cum = 0.0
    for p in productos:
        cum += p["valor_ventas_long"]
        ratio = cum / total_val
        if ratio <= 0.80:
            p["clase_abc"] = "A"
        elif ratio <= 0.95:
            p["clase_abc"] = "B"
        else:
            p["clase_abc"] = "C"

    return {
        "days_short": days_short,
        "days_long": days_long,
        "products": productos,
        "summary": {
            "total_productos": len(productos),
            "agotados": sum(1 for p in productos if p["estado"] == "AGOTADO"),
            "requieren_compra": sum(1 for p in productos if p["requiere_compra"]),
            "sobrestock": sum(1 for p in productos if p["estado"] == "SOBRESTOCK"),
            "valor_inventario": round(sum(p["stock"] * p["cost"] for p in productos), 0),
        },
    }


@router.get("/export/excel")
async def export_inventory_excel(db: DBSession, user: CurrentUser):
    """Descarga inventario completo como Excel (xlsxwriter)."""
    import io
    try:
        import xlsxwriter
    except ImportError:
        raise HTTPException(500, "xlsxwriter no instalado en el servidor")

    from sqlalchemy import text
    rows = (await db.execute(text("""
        SELECT p.sku, p.name, c.name AS categoria, b.name AS marca,
               COALESCE(SUM(s.quantity - s.reserved), 0) AS stock,
               p.cost::float AS costo, p.price::float AS precio,
               (p.price::float - p.cost::float) AS margen_$,
               CASE WHEN p.price > 0 THEN ROUND(((p.price - p.cost) / p.price * 100)::numeric, 1) ELSE 0 END AS margen_pct
        FROM catalog.products p
        LEFT JOIN catalog.categories c ON c.id = p.category_id
        LEFT JOIN catalog.brands b ON b.id = p.brand_id
        LEFT JOIN inventory.stock s ON s.product_id = p.id
        WHERE p.deleted_at IS NULL
        GROUP BY p.id, c.name, b.name
        ORDER BY p.name
    """))).all()

    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {"in_memory": True})
    ws = wb.add_worksheet("Inventario")

    headers = ["SKU", "Nombre", "Categoría", "Marca", "Stock", "Costo", "Precio", "Margen $", "Margen %"]
    bold = wb.add_format({"bold": True, "bg_color": "#FF6B35", "font_color": "white", "border": 1})
    money = wb.add_format({"num_format": "$#,##0"})
    pct = wb.add_format({"num_format": "0.0\"%\""})

    for col, h in enumerate(headers):
        ws.write(0, col, h, bold)
    for ri, r in enumerate(rows, start=1):
        ws.write(ri, 0, r[0] or "")
        ws.write(ri, 1, r[1] or "")
        ws.write(ri, 2, r[2] or "")
        ws.write(ri, 3, r[3] or "")
        ws.write(ri, 4, int(r[4] or 0))
        ws.write(ri, 5, float(r[5] or 0), money)
        ws.write(ri, 6, float(r[6] or 0), money)
        ws.write(ri, 7, float(r[7] or 0), money)
        ws.write(ri, 8, float(r[8] or 0), pct)

    ws.set_column("A:A", 16)
    ws.set_column("B:B", 40)
    ws.set_column("C:D", 18)
    ws.set_column("E:I", 12)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, len(rows), len(headers) - 1)
    wb.close()

    output.seek(0)
    from fastapi.responses import StreamingResponse
    filename = f"inventario_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
