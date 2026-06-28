"""Publicador en Meta Graph API (Instagram + Facebook)."""
from __future__ import annotations

import logging
import os
import time

import requests

log = logging.getLogger(__name__)

META_BASE   = "https://graph.facebook.com/v18.0"
PAGE_ID     = os.environ.get("META_PAGE_ID", "")
IG_ID       = os.environ.get("META_INSTAGRAM_BUSINESS_ID", "")
ACCESS_TOKEN= os.environ.get("META_ACCESS_TOKEN", "")


def _token() -> str:
    t = ACCESS_TOKEN or os.environ.get("META_ACCESS_TOKEN", "")
    if not t:
        raise RuntimeError("META_ACCESS_TOKEN no configurado")
    return t


async def publish_to_meta(post: dict, target: str, dry_run: bool = True) -> dict:
    """Publica post en Instagram y/o Facebook.

    Args:
        post: dict con image_url, caption, hashtags.
        target: 'instagram' | 'facebook'.
        dry_run: si True no toca Meta API.
    """
    if dry_run:
        log.info("[dry-run] publish_to_meta skipped — target=%s post_id=%s", target, post.get("id"))
        return {"dry_run": True, "target": target}

    caption = _build_caption(post)
    image_url = post.get("image_url", "")
    if not image_url:
        raise ValueError("Post sin image_url")

    if target == "instagram":
        return _publish_instagram(image_url, caption)
    elif target == "facebook":
        return _publish_facebook(image_url, caption)
    else:
        raise ValueError(f"Target desconocido: {target}")


def _build_caption(post: dict) -> str:
    caption = post.get("caption", "")
    hashtags = post.get("hashtags", [])
    if hashtags:
        ht_str = " ".join(hashtags)
        if ht_str not in caption:
            caption = f"{caption}\n\n{ht_str}"
    return caption


def _publish_instagram(image_url: str, caption: str) -> dict:
    ig = IG_ID or os.environ.get("META_INSTAGRAM_BUSINESS_ID", "")
    token = _token()
    if not ig:
        raise RuntimeError("META_INSTAGRAM_BUSINESS_ID no configurado")

    # Paso 1: crear media container
    r1 = requests.post(
        f"{META_BASE}/{ig}/media",
        params={
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        },
        timeout=30,
    )
    r1.raise_for_status()
    container_id = r1.json()["id"]
    log.info("IG container creado: %s", container_id)

    # Paso 2: esperar que Meta procese la imagen (FINISHED)
    for attempt in range(12):
        time.sleep(5)
        rs = requests.get(
            f"{META_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=10,
        )
        status_code = rs.json().get("status_code", "")
        log.info("IG container status (%d/12): %s", attempt + 1, status_code)
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            raise RuntimeError(f"IG container procesamiento falló: {rs.json()}")
    else:
        raise RuntimeError("IG container no llegó a FINISHED en 60 segundos")

    # Paso 3: publicar
    r2 = requests.post(
        f"{META_BASE}/{ig}/media_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=30,
    )
    r2.raise_for_status()
    post_id = r2.json()["id"]
    log.info("IG publicado: %s", post_id)
    return {"instagram_post_id": post_id, "container_id": container_id}


def _publish_facebook(image_url: str, caption: str) -> dict:
    page = PAGE_ID or os.environ.get("META_PAGE_ID", "")
    token = _token()
    if not page:
        raise RuntimeError("META_PAGE_ID no configurado")

    r = requests.post(
        f"{META_BASE}/{page}/photos",
        params={
            "url": image_url,
            "caption": caption,
            "access_token": token,
        },
        timeout=30,
    )
    r.raise_for_status()
    post_id = r.json().get("post_id") or r.json().get("id")
    log.info("FB publicado: %s", post_id)
    return {"facebook_post_id": post_id}
