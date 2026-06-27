"""Endpoints SEO — sitemap-data, IndexNow ping."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(prefix="/seo", tags=["seo"])


@router.get("/sitemap-data")
async def sitemap_data(db: AsyncSession = Depends(get_db)):
    """Devuelve todos los slugs publicados en una sola query optimizada."""

    products = await db.execute(
        text("""
            SELECT slug, updated_at,
                   CASE WHEN stock_qty > 0 THEN true ELSE false END AS is_in_stock
            FROM catalog.products
            WHERE is_published = true
            ORDER BY updated_at DESC
        """)
    )

    categories = await db.execute(
        text("""
            SELECT slug, updated_at
            FROM catalog.categories
            WHERE is_active = true
        """)
    )

    posts = await db.execute(
        text("""
            SELECT slug, updated_at, published_at
            FROM content.blog_posts
            WHERE published_at IS NOT NULL
            ORDER BY published_at DESC
        """)
    )

    landings = await db.execute(
        text("""
            SELECT slug, updated_at
            FROM content.seo_landings
            WHERE is_active = true
        """)
    )

    def row_to_dict(row):
        return {k: (v.isoformat() if hasattr(v, 'isoformat') else v)
                for k, v in row._mapping.items()}

    return {
        "products": [row_to_dict(r) for r in products],
        "categories": [row_to_dict(r) for r in categories],
        "posts": [row_to_dict(r) for r in posts],
        "landings": [row_to_dict(r) for r in landings],
    }
