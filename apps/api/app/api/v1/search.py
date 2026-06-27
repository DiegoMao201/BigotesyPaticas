"""Fuzzy product search using pg_trgm trigram similarity."""
from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select, text
from decimal import Decimal

from app.deps import DBSession
from app.models.catalog import Product
from app.models.inventory import Stock

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search_products(
    db: DBSession,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(20, ge=1, le=60),
):
    """Fuzzy product search with trigram similarity (pg_trgm required)."""
    # Normalize query
    q_clean = q.strip()

    # Try trigram similarity first; fall back to ILIKE if extension not available
    try:
        stmt = (
            select(
                Product,
                func.greatest(
                    func.similarity(Product.name, q_clean),
                    func.similarity(func.coalesce(Product.brand, ""), q_clean) * 0.8,
                ).label("sim"),
            )
            .where(
                Product.is_published == True,  # noqa: E712
                or_(
                    func.similarity(Product.name, q_clean) > 0.15,
                    func.similarity(func.coalesce(Product.brand, ""), q_clean) > 0.2,
                    Product.name.ilike(f"%{q_clean}%"),
                    Product.brand.ilike(f"%{q_clean}%"),
                    Product.sku.ilike(f"%{q_clean}%"),
                ),
            )
            .order_by(
                text("sim DESC"),
                Product.name,
            )
            .limit(limit)
        )
        rows = await db.execute(stmt)
        products = rows.all()
    except Exception:
        # pg_trgm not available — fall back to ILIKE
        stmt = (
            select(Product)
            .where(
                Product.is_published == True,  # noqa: E712
                or_(
                    Product.name.ilike(f"%{q_clean}%"),
                    Product.sku.ilike(f"%{q_clean}%"),
                    Product.brand.ilike(f"%{q_clean}%"),
                ),
            )
            .limit(limit)
        )
        rows = await db.execute(stmt)
        products = [(p, None) for p in rows.scalars().all()]

    if not products:
        return []

    # Batch stock lookup
    product_ids = [p.id for p, _ in products]
    stock_stmt = (
        select(Stock.product_id, func.sum(Stock.quantity).label("qty"))
        .where(Stock.product_id.in_(product_ids))
        .group_by(Stock.product_id)
    )
    stock_rows = await db.execute(stock_stmt)
    stock_map = {r.product_id: int(r.qty or 0) for r in stock_rows}

    result = []
    for product, sim in products:
        stock_qty = stock_map.get(product.id, 0)
        result.append({
            "id": str(product.id),
            "sku": product.sku,
            "name": product.name,
            "slug": product.slug,
            "price": float(product.price) if product.price else 0,
            "compare_at_price": float(product.compare_at_price) if product.compare_at_price else None,
            "primary_image_url": product.primary_image_url,
            "brand": product.brand,
            "is_in_stock": stock_qty > 0,
            "stock_qty": stock_qty,
            "similarity": round(float(sim), 3) if sim is not None else None,
        })

    return result


@router.get("/redirect")
async def slug_redirect(
    db: DBSession,
    old: str = Query(..., min_length=1),
):
    """Check if a slug has a 301 redirect registered."""
    stmt = text("""
        UPDATE catalog.slug_redirects
        SET redirect_count = redirect_count + 1,
            last_redirect_at = now()
        WHERE old_slug = :old
        RETURNING new_slug
    """)
    row = await db.execute(stmt, {"old": old})
    result = row.fetchone()
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No redirect found")
    return {"new_slug": result[0]}
