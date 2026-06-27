"""Blog público — listado y detalle de artículos SEO."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.deps import DBSession

router = APIRouter(prefix="/blog", tags=["blog"])


@router.get("/posts")
async def list_posts(
    db: DBSession,
    published: bool = True,
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=100),
) -> dict:
    offset = (page - 1) * per_page
    params: dict = {"per_page": per_page, "offset": offset}

    filters: list[str] = []
    if published:
        filters.append("published_at IS NOT NULL AND published_at <= NOW()")
    if category:
        filters.append("category = :category")
        params["category"] = category

    where = "WHERE " + " AND ".join(filters) if filters else ""

    rows = await db.execute(
        text(f"""
            SELECT id, slug, title, excerpt, cover_image_url, category, keywords,
                   meta_title, meta_description, author, published_at, updated_at, view_count
            FROM content.blog_posts
            {where}
            ORDER BY published_at DESC NULLS LAST
            LIMIT :per_page OFFSET :offset
        """),
        params,
    )

    count_params = {k: v for k, v in params.items() if k not in ("per_page", "offset")}
    total_row = await db.execute(
        text(f"SELECT COUNT(*) FROM content.blog_posts {where}"),
        count_params,
    )
    total = total_row.scalar() or 0

    def _fmt(row) -> dict:
        return {
            "id": str(row["id"]),
            "slug": row["slug"],
            "title": row["title"],
            "excerpt": row["excerpt"],
            "cover_image_url": row["cover_image_url"],
            "category": row["category"],
            "keywords": list(row["keywords"] or []),
            "meta_title": row["meta_title"],
            "meta_description": row["meta_description"],
            "author": row["author"],
            "published_at": row["published_at"].isoformat() if row["published_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            "view_count": row["view_count"],
        }

    posts = [_fmt(r) for r in rows.mappings()]
    return {"posts": posts, "total": total, "page": page, "per_page": per_page}


@router.get("/posts/{slug}")
async def get_post(slug: str, db: DBSession) -> dict:
    row = (
        await db.execute(
            text("""
                SELECT id, slug, title, excerpt, content, cover_image_url, category, keywords,
                       meta_title, meta_description, author, published_at, updated_at, view_count
                FROM content.blog_posts
                WHERE slug = :slug
                  AND published_at IS NOT NULL
                  AND published_at <= NOW()
            """),
            {"slug": slug},
        )
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Post no encontrado")

    await db.execute(
        text("UPDATE content.blog_posts SET view_count = view_count + 1 WHERE slug = :slug"),
        {"slug": slug},
    )
    await db.commit()

    return {
        "id": str(row["id"]),
        "slug": row["slug"],
        "title": row["title"],
        "excerpt": row["excerpt"],
        "content": row["content"],
        "cover_image_url": row["cover_image_url"],
        "category": row["category"],
        "keywords": list(row["keywords"] or []),
        "meta_title": row["meta_title"],
        "meta_description": row["meta_description"],
        "author": row["author"],
        "published_at": row["published_at"].isoformat() if row["published_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "view_count": row["view_count"],
    }


@router.post("/posts", include_in_schema=False)
async def create_post(payload: dict, db: DBSession) -> dict:
    """Endpoint interno para el script de generación. Sin auth (solo accesible desde la red)."""
    post_id = uuid.uuid4()
    await db.execute(
        text("""
            INSERT INTO content.blog_posts (
                id, slug, title, excerpt, content, cover_image_url, category,
                keywords, meta_title, meta_description, author, ai_model, published_at
            ) VALUES (
                :id, :slug, :title, :excerpt, :content, :cover_image_url, :category,
                :keywords, :meta_title, :meta_description, :author, :ai_model, NOW()
            )
            ON CONFLICT (slug) DO UPDATE SET
                title            = EXCLUDED.title,
                excerpt          = EXCLUDED.excerpt,
                content          = EXCLUDED.content,
                cover_image_url  = EXCLUDED.cover_image_url,
                meta_title       = EXCLUDED.meta_title,
                meta_description = EXCLUDED.meta_description,
                keywords         = EXCLUDED.keywords,
                updated_at       = NOW()
        """),
        {
            "id": post_id,
            "slug": payload.get("slug", ""),
            "title": payload.get("title", ""),
            "excerpt": payload.get("excerpt"),
            "content": payload.get("content", ""),
            "cover_image_url": payload.get("cover_image_url"),
            "category": payload.get("category"),
            "keywords": payload.get("keywords", []),
            "meta_title": payload.get("meta_title"),
            "meta_description": payload.get("meta_description"),
            "author": payload.get("author", "Equipo Bigotes y Paticas"),
            "ai_model": payload.get("ai_model", "google/gemini-2.5-flash"),
        },
    )
    await db.commit()
    return {"id": str(post_id), "slug": payload.get("slug"), "ok": True}
