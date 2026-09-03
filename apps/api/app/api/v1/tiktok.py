"""TikTok Content Posting API — conexión OAuth y publicación.

Mientras la app no pase la auditoría de TikTok, cualquier publicación
queda restringida a privacy_level SELF_ONLY (solo la visibiliza el dueño
de la cuenta) — por eso este módulo no se conecta todavía al cron
automático de los otros 5 destinos (Meta); es un flujo manual para
conectar la cuenta y probar publicaciones en modo prueba, hasta que se
apruebe la auditoría.

El callback de OAuth (`/v1/tiktok/oauth/callback`) es público a propósito:
TikTok redirige el navegador del usuario ahí después de que autoriza, sin
ningún header de autenticación nuestro -- la protección contra CSRF es el
`state` de un solo uso guardado en content.tiktok_oauth_state.
"""

from __future__ import annotations

import logging
import os
import secrets
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import DBSession
from app.deps import require_superadmin as get_current_admin_user

router = APIRouter(tags=["tiktok"])

TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"
REDIRECT_URI = "https://api.bigotesypaticas.com/v1/tiktok/oauth/callback"
# video.publish (Direct Post) no está habilitado todavía en el app -- solo
# aparece en el panel de scopes user.info.basic/profile/stats, video.list y
# video.upload. Sin video.publish no se puede usar /post/publish/video/init/
# con PULL_FROM_URL para publicar directo; una vez TikTok habilite ese scope
# (probablemente junto con la auditoría), se agrega de vuelta aquí.
SCOPES = "user.info.basic,video.upload"
PUBLISH_SCOPE = "video.publish"
ADMIN_TIKTOK_PAGE = "https://admin.bigotesypaticas.com/content/tiktok"

_STATE_TTL = timedelta(minutes=10)

# FILE_UPLOAD: los videos viven en el CDN de DigitalOcean (dominio que no
# podemos verificar en el portal de TikTok), así que PULL_FROM_URL fallaría
# con url_ownership_unverified. En su lugar descargamos el mp4 y lo subimos
# nosotros. TikTok exige chunks de 5-64 MB (el último puede ser mayor, hasta
# 128 MB); un video de <= 64 MB va en un solo chunk.
_CHUNK_SIZE = 50 * 1024 * 1024
_SINGLE_CHUNK_MAX = 64 * 1024 * 1024
_MAX_VIDEO_BYTES = 500 * 1024 * 1024

log = logging.getLogger("tiktok")


def _client_key() -> str:
    v = os.environ.get("TIKTOK_CLIENT_KEY", "")
    if not v:
        raise HTTPException(500, "TIKTOK_CLIENT_KEY no configurado")
    return v


def _client_secret() -> str:
    v = os.environ.get("TIKTOK_CLIENT_SECRET", "")
    if not v:
        raise HTTPException(500, "TIKTOK_CLIENT_SECRET no configurado")
    return v


# ── Conexión OAuth (admin) ──────────────────────────────────────────


@router.get("/v1/admin/tiktok/authorize")
async def tiktok_authorize(db: DBSession, _admin=Depends(get_current_admin_user)):
    """Genera la URL de autorización de TikTok. El admin abre esta URL en
    el navegador (no es una llamada XHR) para conectar la cuenta."""
    state = secrets.token_urlsafe(24)
    await db.execute(
        text("INSERT INTO content.tiktok_oauth_state (state) VALUES (:s)"), {"s": state}
    )
    await db.execute(
        text("DELETE FROM content.tiktok_oauth_state WHERE created_at < :cutoff"),
        {"cutoff": datetime.now(UTC) - _STATE_TTL},
    )
    await db.commit()

    params = {
        "client_key": _client_key(),
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
    }
    url = f"{TIKTOK_AUTH_URL}?{httpx.QueryParams(params)}"
    return {"authorize_url": url}


@router.get("/v1/tiktok/oauth/callback")
async def tiktok_oauth_callback(
    db: DBSession,
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
):
    """TikTok redirige aquí el navegador del usuario tras autorizar (o
    rechazar) el acceso. Sin auth nuestra -- se valida con `state`."""
    if error:
        return RedirectResponse(
            f"{ADMIN_TIKTOK_PAGE}?error={error}&detail={error_description or ''}"
        )
    if not code or not state:
        return RedirectResponse(f"{ADMIN_TIKTOK_PAGE}?error=missing_code_or_state")

    row = (
        await db.execute(
            text("SELECT state FROM content.tiktok_oauth_state WHERE state = :s"), {"s": state}
        )
    ).fetchone()
    if not row:
        return RedirectResponse(f"{ADMIN_TIKTOK_PAGE}?error=invalid_or_expired_state")
    await db.execute(text("DELETE FROM content.tiktok_oauth_state WHERE state = :s"), {"s": state})
    await db.commit()

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            TIKTOK_TOKEN_URL,
            data={
                "client_key": _client_key(),
                "client_secret": _client_secret(),
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    body = r.json()
    if r.status_code != 200 or "access_token" not in body:
        log.error("token_exchange_failed body=%r", body)
        return RedirectResponse(
            f"{ADMIN_TIKTOK_PAGE}?error=token_exchange_failed&detail={body!s}"[:500]
        )

    now = datetime.now(UTC)
    open_id = body["open_id"]
    await db.execute(
        text("""
            INSERT INTO content.tiktok_auth
                (open_id, access_token, refresh_token, scope, expires_at, refresh_expires_at, updated_at)
            VALUES (:open_id, :at, :rt, :scope, :exp, :rexp, :now)
            ON CONFLICT (open_id) DO UPDATE SET
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                scope = EXCLUDED.scope,
                expires_at = EXCLUDED.expires_at,
                refresh_expires_at = EXCLUDED.refresh_expires_at,
                updated_at = EXCLUDED.updated_at
        """),
        {
            "open_id": open_id,
            "at": body["access_token"],
            "rt": body["refresh_token"],
            "scope": body.get("scope", SCOPES),
            "exp": now + timedelta(seconds=int(body.get("expires_in", 0))),
            "rexp": now + timedelta(seconds=int(body["refresh_expires_in"]))
            if body.get("refresh_expires_in")
            else None,
            "now": now,
        },
    )
    await db.commit()

    # Nombre visible de la cuenta (user.info.basic). Best-effort: si falla,
    # la conexión igual queda hecha -- solo se pierde el nombre en el admin.
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            u = await client.get(
                f"{TIKTOK_API_BASE}/user/info/",
                params={"fields": "open_id,display_name"},
                headers={"Authorization": f"Bearer {body['access_token']}"},
            )
        display_name = (u.json().get("data", {}).get("user", {}) or {}).get("display_name")
        if display_name:
            await db.execute(
                text("UPDATE content.tiktok_auth SET username=:u WHERE open_id=:o"),
                {"u": display_name, "o": open_id},
            )
            await db.commit()
    except Exception:
        log.warning("user/info falló tras conectar", exc_info=True)

    return RedirectResponse(f"{ADMIN_TIKTOK_PAGE}?connected=1")


@router.get("/v1/admin/tiktok/status")
async def tiktok_status(db: DBSession, _admin=Depends(get_current_admin_user)):
    """Nunca devuelve los tokens -- solo si hay cuenta conectada y su vigencia."""
    row = (
        await db.execute(
            text("""
                SELECT open_id, username, expires_at, refresh_expires_at, updated_at
                FROM content.tiktok_auth ORDER BY updated_at DESC LIMIT 1
            """)
        )
    ).fetchone()
    if not row:
        return {"connected": False}
    return {
        "connected": True,
        "open_id": row.open_id,
        "username": row.username,
        "access_token_expires_at": row.expires_at.isoformat(),
        "refresh_token_expires_at": row.refresh_expires_at.isoformat()
        if row.refresh_expires_at
        else None,
        "updated_at": row.updated_at.isoformat(),
    }


# ── Publicación de prueba (admin) ───────────────────────────────────


class TikTokTestPublish(BaseModel):
    video_url: str
    caption: str = ""


async def _get_valid_token(db: DBSession) -> tuple[str, str]:
    """Devuelve (access_token vigente, scope concedido), refrescando el
    token si ya venció."""
    row = (
        await db.execute(
            text("""
                SELECT id, access_token, refresh_token, scope, expires_at
                FROM content.tiktok_auth ORDER BY updated_at DESC LIMIT 1
            """)
        )
    ).fetchone()
    if not row:
        raise HTTPException(400, "No hay ninguna cuenta de TikTok conectada todavía")

    scope = row.scope or ""
    if row.expires_at > datetime.now(UTC) + timedelta(minutes=2):
        return row.access_token, scope

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            TIKTOK_TOKEN_URL,
            data={
                "client_key": _client_key(),
                "client_secret": _client_secret(),
                "grant_type": "refresh_token",
                "refresh_token": row.refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    body = r.json()
    if r.status_code != 200 or "access_token" not in body:
        log.error("refresh_token falló body=%r", body)
        raise HTTPException(502, f"No se pudo refrescar el token de TikTok: {body!s}"[:500])

    now = datetime.now(UTC)
    await db.execute(
        text("""
            UPDATE content.tiktok_auth
            SET access_token=:at, refresh_token=:rt, expires_at=:exp,
                refresh_expires_at=:rexp, updated_at=:now
            WHERE id=:id
        """),
        {
            "id": row.id,
            "at": body["access_token"],
            "rt": body.get("refresh_token", row.refresh_token),
            "exp": now + timedelta(seconds=int(body.get("expires_in", 0))),
            "rexp": now + timedelta(seconds=int(body["refresh_expires_in"]))
            if body.get("refresh_expires_in")
            else None,
            "now": now,
        },
    )
    await db.commit()
    return body["access_token"], scope


async def _download_video(video_url: str) -> bytes:
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        r = await client.get(video_url)
    if r.status_code != 200:
        raise HTTPException(400, f"No se pudo descargar el video ({r.status_code}): {video_url}")
    data = r.content
    if not data:
        raise HTTPException(400, "El video descargado está vacío")
    if len(data) > _MAX_VIDEO_BYTES:
        raise HTTPException(400, f"Video demasiado grande ({len(data) // (1024 * 1024)} MB)")
    return data


def _chunk_plan(size: int) -> tuple[int, int]:
    """(chunk_size, total_chunk_count) según las reglas de TikTok."""
    if size <= _SINGLE_CHUNK_MAX:
        return size, 1
    return _CHUNK_SIZE, size // _CHUNK_SIZE


async def _upload_chunks(upload_url: str, data: bytes) -> None:
    """PUT de los chunks a la URL que devolvió TikTok en el init. El último
    chunk absorbe el sobrante para no violar el mínimo de 5 MB."""
    size = len(data)
    chunk_size, count = _chunk_plan(size)
    async with httpx.AsyncClient(timeout=300) as client:
        for i in range(count):
            start = i * chunk_size
            end = size if i == count - 1 else start + chunk_size
            r = await client.put(
                upload_url,
                content=data[start:end],
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(end - start),
                    "Content-Range": f"bytes {start}-{end - 1}/{size}",
                },
            )
            if r.status_code not in (200, 201, 206):
                raise HTTPException(
                    502, f"Subida del chunk {i + 1}/{count} falló ({r.status_code}): {r.text[:300]}"
                )


@router.post("/v1/admin/tiktok/test-publish")
async def tiktok_test_publish(
    payload: TikTokTestPublish,
    db: DBSession,
    _admin=Depends(get_current_admin_user),
):
    """Sube un video a TikTok.

    - Con scope `video.publish` (Direct Post): queda publicado; sin auditoría
      TikTok fuerza privacy_level=SELF_ONLY (solo lo ve la cuenta dueña).
    - Solo con `video.upload` (lo que tenemos hoy): va a la bandeja de
      borradores de la app de TikTok y el dueño lo publica con un toque.
    """
    access_token, scope = await _get_valid_token(db)
    direct = PUBLISH_SCOPE in scope.split(",")
    auth = {"Authorization": f"Bearer {access_token}"}
    json_hdr = {**auth, "Content-Type": "application/json; charset=UTF-8"}

    data = await _download_video(payload.video_url)
    chunk_size, count = _chunk_plan(len(data))
    source_info = {
        "source": "FILE_UPLOAD",
        "video_size": len(data),
        "chunk_size": chunk_size,
        "total_chunk_count": count,
    }

    privacy_level: str | None = None
    creator_username: str | None = None
    async with httpx.AsyncClient(timeout=30) as client:
        if direct:
            creator_r = await client.post(
                f"{TIKTOK_API_BASE}/post/publish/creator_info/query/", headers=auth
            )
            creator = creator_r.json()
            if creator_r.status_code != 200 or creator.get("error", {}).get("code") != "ok":
                raise HTTPException(502, f"creator_info/query falló: {creator!s}"[:500])
            options = creator["data"].get("privacy_level_options") or ["SELF_ONLY"]
            privacy_level = "SELF_ONLY" if "SELF_ONLY" in options else options[0]
            creator_username = creator["data"].get("creator_username")
            init_r = await client.post(
                f"{TIKTOK_API_BASE}/post/publish/video/init/",
                headers=json_hdr,
                json={
                    "post_info": {
                        "title": payload.caption[:2200],
                        "privacy_level": privacy_level,
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                    },
                    "source_info": source_info,
                },
            )
        else:
            init_r = await client.post(
                f"{TIKTOK_API_BASE}/post/publish/inbox/video/init/",
                headers=json_hdr,
                json={"source_info": source_info},
            )

    init_body = init_r.json()
    if init_r.status_code != 200 or init_body.get("error", {}).get("code") != "ok":
        log.error("video/init falló body=%r", init_body)
        raise HTTPException(502, f"video/init falló: {init_body!s}"[:500])

    await _upload_chunks(init_body["data"]["upload_url"], data)

    return {
        "publish_id": init_body["data"]["publish_id"],
        "mode": "direct" if direct else "inbox",
        "video_bytes": len(data),
        "privacy_level_used": privacy_level,
        "creator_username": creator_username,
    }


@router.get("/v1/admin/tiktok/publish-status/{publish_id}")
async def tiktok_publish_status(
    publish_id: str,
    db: DBSession,
    _admin=Depends(get_current_admin_user),
):
    access_token, _scope = await _get_valid_token(db)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{TIKTOK_API_BASE}/post/publish/status/fetch/",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
        )
    body = r.json()
    if r.status_code != 200:
        raise HTTPException(502, f"status/fetch falló: {body!s}"[:500])
    return body.get("data", {})
