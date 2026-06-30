#!/usr/bin/env python3
"""Publica feed posts aprobados en Instagram y Facebook — Bigotes y Paticas.

Corre cada 5 minutos via cron (igual que publish_stories.py).
Instagram: imagen en feed del perfil (permanente).
Facebook:  foto con caption en el muro de la página (permanente).
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, "/app")

try:
    import psycopg2
except ModuleNotFoundError:
    import psycopg as psycopg2

import requests

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

_BOGOTA   = ZoneInfo("America/Bogota")
META_BASE = "https://graph.facebook.com/v25.0"
DB_URL    = os.environ.get("DATABASE_URL_SYNC", "").replace(
    "postgresql+asyncpg://", "postgresql://"
).replace("postgresql+psycopg://", "postgresql://")


def _page_token() -> str:
    t = os.environ.get("META_MESSENGER_TOKEN", "")
    if not t:
        raise RuntimeError("META_MESSENGER_TOKEN no configurado")
    return t


def get_pending_feed_posts(cur) -> list[dict]:
    cur.execute("""
        SELECT id, base_image_url, caption, swipe_up_url
        FROM content.story_posts
        WHERE post_type = 'feed_post'
          AND status = 'approved'
        ORDER BY updated_at ASC
        LIMIT 5
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def publish_instagram_feed(image_url: str, caption: str) -> str:
    """Publica imagen en el feed de Instagram Business."""
    ig_id      = os.environ.get("META_INSTAGRAM_BUSINESS_ID", "")
    page_token = _page_token()
    if not ig_id:
        raise RuntimeError("META_INSTAGRAM_BUSINESS_ID no configurado")

    # Paso 1: crear contenedor
    r1 = requests.post(
        f"{META_BASE}/{ig_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": page_token},
        timeout=30,
    )
    r1.raise_for_status()
    data1 = r1.json()
    if "error" in data1:
        raise RuntimeError(f"IG media container error: {data1['error']}")
    creation_id = data1["id"]
    log.info("  IG container creado: %s", creation_id)

    # Paso 2: publicar
    r2 = requests.post(
        f"{META_BASE}/{ig_id}/media_publish",
        data={"creation_id": creation_id, "access_token": page_token},
        timeout=30,
    )
    r2.raise_for_status()
    data2 = r2.json()
    if "error" in data2:
        raise RuntimeError(f"IG publish error: {data2['error']}")
    return data2.get("id", "")


def publish_facebook_feed(image_url: str, caption: str, link_url: str | None = None) -> str:
    """Publica foto en el feed de la página de Facebook.

    El link de contacto va en el caption como texto clickeable en FB.
    """
    page_id    = os.environ.get("META_PAGE_ID", "")
    page_token = _page_token()
    if not page_id:
        raise RuntimeError("META_PAGE_ID no configurado")

    # Añadir link explícito al caption para Facebook (es clickeable en FB)
    full_caption = caption
    if link_url and link_url not in caption:
        full_caption = caption + f"\n\n🔗 {link_url}"

    r = requests.post(
        f"{META_BASE}/{page_id}/photos",
        data={"url": image_url, "message": full_caption, "access_token": page_token},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"FB photo post error: {data['error']}")
    return data.get("post_id") or data.get("id", "")


def mark_published(cur, conn, post_id: str, ig_id: str, fb_id: str) -> None:
    cur.execute("""
        UPDATE content.story_posts
        SET status = 'published',
            published_at = NOW(),
            instagram_story_id = %s,
            facebook_story_id  = %s,
            updated_at = NOW()
        WHERE id = %s
    """, (ig_id, fb_id, post_id))
    conn.commit()


def mark_failed(cur, conn, post_id: str, error: str) -> None:
    cur.execute("""
        UPDATE content.story_posts
        SET status = 'failed',
            error_message = %s,
            updated_at = NOW()
        WHERE id = %s
    """, (error[:500], post_id))
    conn.commit()


def main() -> None:
    if not DB_URL:
        log.error("DATABASE_URL_SYNC no configurada")
        sys.exit(1)

    conn = psycopg2.connect(DB_URL, connect_timeout=10)
    cur  = conn.cursor()

    posts = get_pending_feed_posts(cur)
    if not posts:
        log.info("Sin feed posts aprobados pendientes de publicar")
        conn.close()
        return

    log.info("%d feed post(s) aprobados para publicar", len(posts))

    for post in posts:
        pid       = post["id"]
        image_url = post["base_image_url"]
        caption   = post["caption"] or ""
        link_url  = post["swipe_up_url"]

        log.info("Publicando feed post %s …", pid)
        ig_post_id = ""
        fb_post_id = ""
        errors: list[str] = []

        try:
            ig_post_id = publish_instagram_feed(image_url, caption)
            log.info("  IG feed OK: %s", ig_post_id)
        except Exception as e:
            errors.append(f"IG: {e}")
            log.error("  IG feed FAIL: %s", e)

        try:
            fb_post_id = publish_facebook_feed(image_url, caption, link_url)
            log.info("  FB feed OK: %s", fb_post_id)
        except Exception as e:
            errors.append(f"FB: {e}")
            log.error("  FB feed FAIL: %s", e)

        if ig_post_id or fb_post_id:
            mark_published(cur, conn, pid, ig_post_id, fb_post_id)
            log.info("  Publicado — IG=%s FB=%s", ig_post_id, fb_post_id)
        else:
            mark_failed(cur, conn, pid, " | ".join(errors))
            log.error("  FALLÓ en ambas plataformas")

    conn.close()
    log.info("Fin publish_feed_posts")


if __name__ == "__main__":
    main()
