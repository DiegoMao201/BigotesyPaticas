"""Publicador en Meta Graph API (Instagram + Facebook)."""

from __future__ import annotations

import logging
import os
import time

import requests

log = logging.getLogger(__name__)

META_BASE = "https://graph.facebook.com/v18.0"
PAGE_ID = os.environ.get("META_PAGE_ID", "")
IG_ID = os.environ.get("META_INSTAGRAM_BUSINESS_ID", "")
ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")


def _token(platform: str = "instagram") -> str:
    """Devuelve el token correcto según plataforma.

    Facebook page posting requiere Page Access Token (pages_manage_posts).
    Instagram y CAPI usan el System User Token.
    """
    if platform == "facebook":
        t = os.environ.get("META_MESSENGER_TOKEN") or os.environ.get("META_ACCESS_TOKEN", "")
    else:
        t = os.environ.get("META_ACCESS_TOKEN", "")
    if not t:
        raise RuntimeError(f"Token Meta no configurado para {platform}")
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

    caption = _build_caption(post, platform=target)
    image_url = post.get("image_url", "")
    if not image_url:
        raise ValueError("Post sin image_url")

    if target == "instagram":
        return _publish_instagram(image_url, caption)
    elif target == "facebook":
        return _publish_facebook(image_url, caption, token=_token("facebook"))
    else:
        raise ValueError(f"Target desconocido: {target}")


def _ensure_https(url: str) -> str:
    if url and not url.startswith("http"):
        return "https://" + url
    return url


def _build_caption(post: dict, platform: str = "facebook") -> str:
    import re

    caption = post.get("caption", "") or ""
    hashtags = post.get("hashtags", [])
    cta_url = _ensure_https(post.get("cta_url", "") or "")

    # Normalizar todas las URLs sueltas (www.xxx) a https://
    caption = re.sub(r"(?<![/\w])(www\.[a-zA-Z0-9.\-]+\.[a-z]{2,})", r"https://\1", caption)

    if platform == "instagram":
        # Instagram no permite links clicables en caption — guiar al bio
        if cta_url and "bio" not in caption.lower() and "link en bio" not in caption.lower():
            caption = caption + "\n\n🔗 Link en bio para visitar nuestra tienda"
    else:
        # Facebook: asegurar que el cta_url aparece con https:// al final
        if cta_url and cta_url not in caption:
            caption = caption + f"\n\n👉 {cta_url}"

    if hashtags:
        ht_str = " ".join(hashtags)
        if ht_str not in caption:
            caption = f"{caption}\n\n{ht_str}"
    return caption


def _publish_instagram(image_url: str, caption: str) -> dict:
    ig = IG_ID or os.environ.get("META_INSTAGRAM_BUSINESS_ID", "")
    token = _token("instagram")
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


def _publish_facebook(image_url: str, caption: str, token: str = "") -> dict:
    page = PAGE_ID or os.environ.get("META_PAGE_ID", "")
    token = token or _token("facebook")
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
