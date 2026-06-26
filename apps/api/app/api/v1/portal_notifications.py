"""Portal Notifications — SSE stream + helpers para crear notificaciones bidireccionales."""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import and_, select, update

from app.api.v1.portal_auth import PortalUser
from app.config import get_settings
from app.deps import DBSession
from app.models.crm import Customer
from app.models.portal import PortalNotification

router = APIRouter(prefix="/portal/notifications", tags=["portal"])

_SETTINGS = get_settings()
_HEARTBEAT_SEC = 20


# ── helpers (llamados desde otros módulos) ────────────────────────────────────

async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(_SETTINGS.redis_url, decode_responses=True)


async def notify_customer(
    db,
    customer_id: uuid.UUID | str,
    *,
    notif_type: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> None:
    """Inserta notificación en DB y publica en canal Redis del cliente."""
    cid = uuid.UUID(str(customer_id))
    notif = PortalNotification(
        customer_id=cid,
        is_admin=False,
        type=notif_type,
        title=title,
        body=body,
        data=data or {},
    )
    db.add(notif)
    await db.flush()

    payload = json.dumps({
        "id": str(notif.id),
        "type": notif_type,
        "title": title,
        "body": body,
        "created_at": datetime.now(UTC).isoformat(),
        "data": data or {},
    })
    try:
        r = await _get_redis()
        await r.publish(f"portal:notify:{cid}", payload)
        await r.aclose()
    except Exception:
        pass  # Redis down no bloquea la operación principal


async def notify_admins(
    db,
    *,
    notif_type: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> None:
    """Inserta notificación global para admins y publica en canal Redis admin."""
    notif = PortalNotification(
        customer_id=None,
        is_admin=True,
        type=notif_type,
        title=title,
        body=body,
        data=data or {},
    )
    db.add(notif)
    await db.flush()

    payload = json.dumps({
        "id": str(notif.id),
        "type": notif_type,
        "title": title,
        "body": body,
        "created_at": datetime.now(UTC).isoformat(),
        "data": data or {},
    })
    try:
        r = await _get_redis()
        await r.publish("admin:notify", payload)
        await r.aclose()
    except Exception:
        pass


# ── schemas ───────────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    body: str
    is_admin: bool
    read_at: str | None
    created_at: str
    data: dict


def _notif_out(n: PortalNotification) -> NotificationOut:
    return NotificationOut(
        id=str(n.id),
        type=n.type,
        title=n.title,
        body=n.body,
        is_admin=n.is_admin,
        read_at=n.read_at.isoformat() if n.read_at else None,
        created_at=n.created_at.isoformat(),
        data=n.data or {},
    )


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    db: DBSession,
    customer: Customer = PortalUser,
    unread_only: bool = False,
) -> list[NotificationOut]:
    q = select(PortalNotification).where(
        PortalNotification.customer_id == customer.id,
        PortalNotification.is_admin == False,  # noqa: E712
    )
    if unread_only:
        q = q.where(PortalNotification.read_at == None)  # noqa: E711
    q = q.order_by(PortalNotification.created_at.desc()).limit(50)
    rows = (await db.execute(q)).scalars().all()
    return [_notif_out(n) for n in rows]


@router.get("/unread-count")
async def unread_count(
    db: DBSession,
    customer: Customer = PortalUser,
) -> dict:
    from sqlalchemy import func
    result = await db.execute(
        select(func.count()).where(
            PortalNotification.customer_id == customer.id,
            PortalNotification.is_admin == False,  # noqa: E712
            PortalNotification.read_at == None,  # noqa: E711
        )
    )
    return {"unread": result.scalar_one()}


@router.post("/read-all")
async def mark_all_read(
    db: DBSession,
    customer: Customer = PortalUser,
) -> dict:
    now = datetime.now(UTC)
    await db.execute(
        update(PortalNotification)
        .where(
            PortalNotification.customer_id == customer.id,
            PortalNotification.read_at == None,  # noqa: E711
        )
        .values(read_at=now)
    )
    await db.commit()
    return {"ok": True}


@router.get("/events")
async def portal_events(customer: Customer = PortalUser):
    """Server-Sent Events — mantiene la conexión y envía notificaciones en tiempo real."""
    customer_id = str(customer.id)

    async def stream():
        try:
            r = await _get_redis()
            pubsub = r.pubsub()
            await pubsub.subscribe(f"portal:notify:{customer_id}")
            yield "data: {\"type\": \"connected\"}\n\n"
            last_heartbeat = asyncio.get_event_loop().time()
            while True:
                now = asyncio.get_event_loop().time()
                if now - last_heartbeat >= _HEARTBEAT_SEC:
                    yield ": heartbeat\n\n"
                    last_heartbeat = now
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("data"):
                    yield f"data: {msg['data']}\n\n"
                await asyncio.sleep(0)
        except Exception:
            yield "data: {\"type\": \"error\"}\n\n"
        finally:
            try:
                await pubsub.unsubscribe(f"portal:notify:{customer_id}")
                await r.aclose()
            except Exception:
                pass

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Endpoint interno para alertas del sistema (llamado por cron del servidor) ───

@router.post("/internal/disk-alert")
async def disk_alert_internal(request: Request, db: DBSession) -> dict:
    """Solo accesible con X-Internal-Secret. Usado por cron de monitoreo del disco."""
    configured = os.getenv("INTERNAL_ALERT_SECRET", "")
    received = request.headers.get("X-Internal-Secret", "")
    if not configured or received != configured:
        raise HTTPException(status_code=403, detail="Forbidden")

    usage = request.headers.get("X-Disk-Usage", "?")
    await notify_admins(
        db,
        notif_type="general",
        title="⚠️ Disco al 75%+ en el servidor",
        body=f"Uso actual: {usage}%. Ejecuta limpieza de Docker para liberar espacio.",
        data={"disk_usage_pct": usage, "mount": "/mnt/docker_data"},
    )
    await db.commit()
    return {"ok": True, "usage": usage}


# ── SSE para admin ─────────────────────────────────────────────────────────────

admin_router = APIRouter(prefix="/admin/portal-events", tags=["admin"])


@admin_router.get("")
async def admin_events():
    """SSE stream para el panel admin — recibe notificaciones de nuevos pedidos/citas/clientes."""
    async def stream():
        try:
            r = await _get_redis()
            pubsub = r.pubsub()
            await pubsub.subscribe("admin:notify")
            yield "data: {\"type\": \"connected\"}\n\n"
            last_heartbeat = asyncio.get_event_loop().time()
            while True:
                now = asyncio.get_event_loop().time()
                if now - last_heartbeat >= _HEARTBEAT_SEC:
                    yield ": heartbeat\n\n"
                    last_heartbeat = now
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("data"):
                    yield f"data: {msg['data']}\n\n"
                await asyncio.sleep(0)
        except Exception:
            yield "data: {\"type\": \"error\"}\n\n"
        finally:
            try:
                await pubsub.unsubscribe("admin:notify")
                await r.aclose()
            except Exception:
                pass

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
