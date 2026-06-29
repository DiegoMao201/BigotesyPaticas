#!/usr/bin/env python3
"""Worker de publicación de Stories — Bigotes y Paticas.

Cron integrado en Dockerfile CMD cada 5 minutos.
Publica stories aprobadas en Instagram + Facebook via Graph API.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, "/app")

try:
    import psycopg2
except ModuleNotFoundError:
    import psycopg as psycopg2

import requests

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

_BOGOTA    = ZoneInfo("America/Bogota")
META_BASE  = "https://graph.facebook.com/v18.0"
DB_URL     = os.environ.get("DATABASE_URL_SYNC", "").replace(
    "postgresql+asyncpg://", "postgresql://"
).replace("postgresql+psycopg://", "postgresql://")


def _token() -> str:
    t = os.environ.get("META_ACCESS_TOKEN", "")
    if not t:
        raise RuntimeError("META_ACCESS_TOKEN no configurado")
    return t


def get_config(cur) -> dict:
    cur.execute("SELECT key, value FROM content.engine_config WHERE key LIKE 'stories%'")
    return {r[0]: r[1] for r in cur.fetchall()}


def get_pending_stories(cur) -> list[dict]:
    now          = datetime.now(_BOGOTA).replace(tzinfo=None)
    window_start = now - timedelta(hours=1)
    cur.execute("""
        SELECT * FROM content.story_posts
        WHERE status = 'approved'
          AND scheduled_at <= %s
          AND scheduled_at >= %s
        ORDER BY scheduled_at ASC
        LIMIT 10
    """, (now, window_start))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def publish_ig_story(video_url: str, caption: str) -> str:
    """Publica video story en Instagram. Retorna ig_story_id."""
    ig_id = os.environ.get("META_INSTAGRAM_BUSINESS_ID", "")
    token = _token()
    if not ig_id:
        raise RuntimeError("META_INSTAGRAM_BUSINESS_ID no configurado")

    # Step 1: crear container de video story
    r = requests.post(
        f"{META_BASE}/{ig_id}/media",
        params={
            "media_type": "STORIES",
            "video_url": video_url,
            "caption": caption[:2200],
            "access_token": token,
        },
        timeout=60,
    )
    r.raise_for_status()
    container_id = r.json()["id"]
    log.info("IG story container: %s", container_id)

    # Step 2: esperar que el video se procese (polling)
    for attempt in range(20):
        time.sleep(8)
        s = requests.get(
            f"{META_BASE}/{container_id}",
            params={"fields": "status_code,status", "access_token": token},
            timeout=30,
        )
        s.raise_for_status()
        status_code = s.json().get("status_code", "")
        log.info("IG story status: %s (intento %d)", status_code, attempt + 1)
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            raise RuntimeError(f"IG story processing error: {s.json()}")

    # Step 3: publicar
    r2 = requests.post(
        f"{META_META_BASE}/{ig_id}/media_publish" if False else f"{META_BASE}/{ig_id}/media_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=30,
    )
    r2.raise_for_status()
    story_id = r2.json()["id"]
    log.info("IG story publicada: %s", story_id)
    return story_id


def publish_fb_story(video_url: str) -> str:
    """Publica video story en Facebook Page via resumable upload. Retorna fb_story_id."""
    page_id    = os.environ.get("META_PAGE_ID", "")
    page_token = os.environ.get("META_MESSENGER_TOKEN") or _token()
    if not page_id:
        raise RuntimeError("META_PAGE_ID no configurado")

    # Descargar video desde CDN
    video_bytes = requests.get(video_url, timeout=120).content
    file_size   = len(video_bytes)

    # Fase 1: iniciar sesión de upload
    start_r = requests.post(
        f"{META_BASE}/{page_id}/video_stories",
        data={"upload_phase": "start", "file_size": file_size, "access_token": page_token},
        timeout=30,
    )
    start_r.raise_for_status()
    start_data = start_r.json()
    video_id   = start_data["video_id"]
    upload_url = start_data["upload_url"]
    log.info("FB story upload session: %s", video_id)

    # Fase 2: transferir bytes
    transfer_r = requests.post(
        upload_url,
        headers={
            "Authorization": f"OAuth {page_token}",
            "offset": "0",
            "file_size": str(file_size),
            "Content-Type": "video/mp4",
        },
        data=video_bytes,
        timeout=180,
    )
    transfer_r.raise_for_status()
    log.info("FB story transferida: %s", transfer_r.json().get("message", "")[:80])

    # Fase 3: finalizar
    finish_r = requests.post(
        f"{META_BASE}/{page_id}/video_stories",
        data={"upload_phase": "finish", "video_id": video_id, "access_token": page_token},
        timeout=30,
    )
    finish_r.raise_for_status()
    story_id = finish_r.json().get("post_id") or finish_r.json().get("id", "")
    log.info("FB story publicada: %s", story_id)
    return story_id


async def publish_story(story: dict, dry_run: bool, cur, conn) -> bool:
    story_id = str(story["id"])

    cur.execute(
        "UPDATE content.story_posts SET status='publishing', updated_at=NOW() WHERE id=%s",
        (story_id,)
    )
    conn.commit()

    ig_id = fb_id = None
    error = None

    if dry_run:
        log.info("[dry-run] Story %s — NO se publica en Meta", story_id[:8])
    else:
        video_url = story.get("video_url", "")
        caption   = story.get("caption", "") or ""
        if not video_url:
            error = "Sin video_url"
        else:
            try:
                ig_id = publish_ig_story(video_url, caption)
            except Exception as e:
                log.warning("IG story falló: %s", e)
                error = str(e)[:300]

            try:
                fb_id = publish_fb_story(video_url)
            except Exception as e:
                log.warning("FB story falló: %s", e)
                if not error:
                    error = str(e)[:300]

    now = datetime.now(_BOGOTA).replace(tzinfo=None)
    if error and not ig_id and not fb_id:
        cur.execute("""
            UPDATE content.story_posts
            SET status='failed', error_message=%s, updated_at=%s
            WHERE id=%s
        """, (error, now, story_id))
        conn.commit()
        return False

    cur.execute("""
        UPDATE content.story_posts
        SET status='published', published_at=%s, expires_at=%s,
            instagram_story_id=%s, facebook_story_id=%s,
            dry_run=%s, error_message=NULL, updated_at=%s
        WHERE id=%s
    """, (now, now + timedelta(hours=24), ig_id, fb_id, dry_run, now, story_id))
    conn.commit()
    log.info("Story %s publicada IG=%s FB=%s dry=%s", story_id[:8], ig_id, fb_id, dry_run)
    return True


async def run():
    if not DB_URL:
        log.error("DATABASE_URL_SYNC no configurada"); sys.exit(1)

    conn = psycopg2.connect(DB_URL, connect_timeout=10)
    cur  = conn.cursor()

    cfg = get_config(cur)
    if cfg.get("stories_active") != "true":
        log.info("Stories engine inactivo — exit"); conn.close(); return

    dry_run = cfg.get("stories_dry_run_mode") == "true"
    stories = get_pending_stories(cur)

    if not stories:
        log.info("Sin stories aprobadas pendientes")
        conn.close(); return

    log.info("Publicando %d stories (dry_run=%s)...", len(stories), dry_run)
    ok = failed = 0
    for story in stories:
        success = await publish_story(story, dry_run, cur, conn)
        if success: ok += 1
        else: failed += 1

    conn.close()
    log.info("Stories — publicadas: %d, fallidas: %d", ok, failed)


if __name__ == "__main__":
    asyncio.run(run())
