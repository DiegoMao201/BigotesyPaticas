"""Blog público — listado y detalle de artículos SEO."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.deps import DBSession
from app.services.seo_notifications import notify_indexnow

router = APIRouter(prefix="/blog", tags=["blog"])

_background_tasks: set[asyncio.Task] = set()


@router.get("/posts")
async def list_posts(
    db: DBSession,
    published: bool = True,
    category: str | None = Query(None),
    # /blog no debe mostrar las noticias y /noticias no debe mostrar el blog:
    # son dos secciones distintas y si una URL sale en las dos, Google lo lee
    # como contenido duplicado.
    exclude_category: str | None = Query(None),
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
    if exclude_category:
        filters.append("(category IS DISTINCT FROM :exclude_category)")
        params["exclude_category"] = exclude_category

    where = "WHERE " + " AND ".join(filters) if filters else ""

    rows = await db.execute(
        text(f"""
            SELECT id, slug, title, excerpt, cover_image_url, category, keywords,
                   meta_title, meta_description, author, published_at, updated_at, view_count,
                   source_url, source_name, video_url
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
            "source_url": row["source_url"],
            "source_name": row["source_name"],
            "video_url": row["video_url"],
        }

    posts = [_fmt(r) for r in rows.mappings()]
    return {"posts": posts, "total": total, "page": page, "per_page": per_page}


@router.get("/posts/{slug}")
async def get_post(slug: str, db: DBSession) -> dict:
    row = (
        (
            await db.execute(
                text("""
                SELECT id, slug, title, excerpt, content, cover_image_url, category, keywords,
                       meta_title, meta_description, author, published_at, updated_at, view_count,
                       source_url, source_name, video_url
                FROM content.blog_posts
                WHERE slug = :slug
                  AND published_at IS NOT NULL
                  AND published_at <= NOW()
            """),
                {"slug": slug},
            )
        )
        .mappings()
        .first()
    )

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
        "source_url": row["source_url"],
        "source_name": row["source_name"],
        "video_url": row["video_url"],
    }


@router.post("/posts", include_in_schema=False)
async def create_post(payload: dict, db: DBSession) -> dict:
    """Endpoint interno para el script de generación. Sin auth (solo accesible desde la red)."""
    post_id = uuid.uuid4()
    await db.execute(
        text("""
            INSERT INTO content.blog_posts (
                id, slug, title, excerpt, content, cover_image_url, category,
                keywords, meta_title, meta_description, author, ai_model, published_at,
                source_url, source_name, video_url, story_id
            ) VALUES (
                :id, :slug, :title, :excerpt, :content, :cover_image_url, :category,
                :keywords, :meta_title, :meta_description, :author, :ai_model,
                CASE WHEN :publicar THEN NOW() ELSE NULL END,
                :source_url, :source_name, :video_url, :story_id
            )
            ON CONFLICT (slug) DO UPDATE SET
                title            = EXCLUDED.title,
                excerpt          = EXCLUDED.excerpt,
                content          = EXCLUDED.content,
                cover_image_url  = EXCLUDED.cover_image_url,
                meta_title       = EXCLUDED.meta_title,
                meta_description = EXCLUDED.meta_description,
                keywords         = EXCLUDED.keywords,
                source_url       = EXCLUDED.source_url,
                source_name      = EXCLUDED.source_name,
                video_url        = EXCLUDED.video_url,
                story_id         = COALESCE(EXCLUDED.story_id, content.blog_posts.story_id),
                -- una noticia se crea como borrador (publicar=false) cuando se arma la
                -- pieza y se publica sola cuando Diego la aprueba y el cron la saca.
                -- COALESCE para no re-publicar ni borrar la fecha original.
                published_at     = COALESCE(content.blog_posts.published_at, EXCLUDED.published_at),
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
            "publicar": bool(payload.get("publicar", True)),
            "source_url": payload.get("source_url"),
            "source_name": payload.get("source_name"),
            "video_url": payload.get("video_url"),
            "story_id": payload.get("story_id"),
        },
    )
    await db.commit()
    slug = payload.get("slug", "")
    seccion = "noticias" if payload.get("category") == "noticias" else "blog"
    if payload.get("publicar", True):
        # avisar a los buscadores solo cuando la pieza ya está visible; pedirles que
        # indexen un borrador es pedirles que vuelvan a una página que no existe.
        _task = asyncio.create_task(
            notify_indexnow(
                [
                    f"https://bigotesypaticas.com/{seccion}/{slug}",
                    f"https://bigotesypaticas.com/{seccion}",
                    "https://bigotesypaticas.com/sitemap.xml",
                ]
            )
        )
        _background_tasks.add(_task)
        _task.add_done_callback(_background_tasks.discard)
    return {"id": str(post_id), "slug": slug, "seccion": seccion, "ok": True}


@router.post("/posts/{slug}/publicar", include_in_schema=False)
async def publicar_post(slug: str, db: DBSession) -> dict:
    """Saca del borrador una landing y avisa a los buscadores.

    La landing de una noticia se crea cuando se arma el video, pero NO se publica:
    Diego aprueba en el admin y el cron publica la pieza; ahí mismo se llama aquí.
    Si nadie aprueba, la landing nunca se hace pública, que es justo la regla.
    """
    row = (
        (
            await db.execute(
                text("""
                    UPDATE content.blog_posts
                    SET published_at = COALESCE(published_at, NOW()), updated_at = NOW()
                    WHERE slug = :slug
                    RETURNING slug, category, published_at
                """),
                {"slug": slug},
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Landing no encontrada")
    await db.commit()

    seccion = "noticias" if row["category"] == "noticias" else "blog"
    _task = asyncio.create_task(
        notify_indexnow(
            [
                f"https://bigotesypaticas.com/{seccion}/{slug}",
                f"https://bigotesypaticas.com/{seccion}",
                "https://bigotesypaticas.com/sitemap.xml",
            ]
        )
    )
    _background_tasks.add(_task)
    _task.add_done_callback(_background_tasks.discard)
    return {"slug": slug, "seccion": seccion, "published_at": row["published_at"].isoformat(), "ok": True}
