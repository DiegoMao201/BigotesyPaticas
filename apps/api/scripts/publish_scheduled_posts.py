#!/usr/bin/env python3
"""Worker de publicación — Sprint 6A.

Cron cada 5 minutos:
  */5 * * * * docker exec <api> python scripts/publish_scheduled_posts.py

Publica posts aprobados cuyo scheduled_at <= NOW.
Respeta kill-switch y dry_run_mode.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

UTC = UTC

_BOGOTA = ZoneInfo("America/Bogota")

sys.path.insert(0, "/app")

try:
    import psycopg2
except ModuleNotFoundError:
    import psycopg as psycopg2  # type: ignore[no-redef]

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DB_URL = (
    os.environ.get("DATABASE_URL_SYNC", "")
    .replace("postgresql+psycopg://", "postgresql://")
    .replace("postgresql+asyncpg://", "postgresql://")
)

MAX_RETRIES = 3


def get_config(cur) -> dict:
    cur.execute("SELECT key, value FROM content.engine_config")
    return {r[0]: r[1] for r in cur.fetchall()}


def get_pending_posts(cur) -> list[dict]:
    # scheduled_at se almacena como hora Colombia naive → comparar con hora Colombia
    now = datetime.now(_BOGOTA).replace(tzinfo=None)
    window_start = now - timedelta(hours=1)
    cur.execute(
        """
        SELECT * FROM content.scheduled_posts
        WHERE status = 'approved'
          AND scheduled_at <= %s
          AND scheduled_at >= %s
        ORDER BY scheduled_at ASC
        LIMIT 20
    """,
        (now, window_start),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]


async def publish_post(post: dict, dry_run: bool, cur, conn) -> bool:
    post_id = str(post["id"])
    # Marcar como publishing
    cur.execute(
        "UPDATE content.scheduled_posts SET status = 'publishing', updated_at = NOW() WHERE id = %s",
        (post_id,),
    )
    conn.commit()

    ig_id = fb_id = None
    error = None

    if dry_run:
        log.info("[dry-run] Post %s — NO se publica en Meta", post_id[:8])
        ig_id = None
        fb_id = None
    else:
        from app.services.meta_publisher import publish_to_meta

        platforms = post.get("target_platforms") or ["instagram", "facebook"]
        ig_error = fb_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Solo publicar en plataformas que aún no tienen ID (evita duplicados en retry)
                if "instagram" in platforms and not ig_id:
                    try:
                        result = await publish_to_meta(post, "instagram", dry_run=False)
                        ig_id = result.get("instagram_post_id")
                    except Exception as e_ig:
                        ig_error = str(e_ig)
                        log.warning("IG error intento %d: %s", attempt, e_ig)
                if "facebook" in platforms and not fb_id:
                    try:
                        result = await publish_to_meta(post, "facebook", dry_run=False)
                        fb_id = result.get("facebook_post_id")
                    except Exception as e_fb:
                        fb_error = str(e_fb)
                        log.warning("FB error intento %d: %s", attempt, e_fb)
                # Si al menos IG publicó, no hay que reintentar IG
                if ig_id or (not ig_id and attempt == MAX_RETRIES):
                    break
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2**attempt)
            except Exception as e:
                error = str(e)
                log.warning("Error general intento %d/%d: %s", attempt, MAX_RETRIES, e)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2**attempt)
        # Consolidar error final
        if not error:
            errors = [e for e in [ig_error, fb_error] if e]
            error = " | ".join(errors) if errors else None

    now = datetime.now(UTC)
    if error and not ig_id and not fb_id:
        # Ambas plataformas fallaron — marcar como failed
        cur.execute(
            """
            UPDATE content.scheduled_posts
            SET status = 'failed', publish_error = %s, updated_at = %s
            WHERE id = %s
        """,
            (error[:500], now, post_id),
        )
        log.error("Post %s FAILED: %s", post_id[:8], error)
        conn.commit()
        return False
    else:
        # Al menos una plataforma publicó — guardar error parcial si aplica
        partial_error = error if (ig_id and not fb_id) or (fb_id and not ig_id) else None
        if partial_error:
            log.warning(
                "Post %s publicación parcial — IG=%s FB=%s error=%s",
                post_id[:8],
                ig_id,
                fb_id,
                partial_error[:200],
            )
        cur.execute(
            """
            UPDATE content.scheduled_posts
            SET status = 'published', published_at = %s, updated_at = %s,
                instagram_post_id = %s, facebook_post_id = %s,
                dry_run = %s, publish_error = %s
            WHERE id = %s
        """,
            (
                now,
                now,
                ig_id,
                fb_id,
                dry_run,
                partial_error[:500] if partial_error else None,
                post_id,
            ),
        )
        conn.commit()
        log.info("Post %s publicado IG=%s FB=%s dry=%s", post_id[:8], ig_id, fb_id, dry_run)
        return True


async def run():
    if not DB_URL:
        log.error("DATABASE_URL_SYNC no configurada")
        sys.exit(1)

    conn = psycopg2.connect(DB_URL, connect_timeout=10)
    cur = conn.cursor()

    cfg = get_config(cur)
    if cfg.get("is_active") != "true":
        log.info("Engine inactivo (is_active=false) — exit limpio")
        conn.close()
        return

    dry_run = cfg.get("dry_run_mode") == "true"
    posts = get_pending_posts(cur)

    if not posts:
        log.info("Sin posts aprobados pendientes de publicar")
        conn.close()
        return

    log.info("Publicando %d posts (dry_run=%s)...", len(posts), dry_run)
    ok = failed = 0
    for post in posts:
        success = await publish_post(post, dry_run, cur, conn)
        if success:
            ok += 1
        else:
            failed += 1

    conn.close()
    log.info("Completado — publicados: %d, fallidos: %d", ok, failed)


if __name__ == "__main__":
    asyncio.run(run())
