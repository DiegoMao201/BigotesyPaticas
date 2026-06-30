"""Admin API — Stories IA — Bigotes y Paticas."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_superadmin as get_current_admin_user

router = APIRouter(prefix="/v1/admin/stories", tags=["stories"])
_BOGOTA = ZoneInfo("America/Bogota")


# ── Schemas ───────────────────────────────────────────────────────────────────

class StoryStatusUpdate(BaseModel):
    status: str  # 'approved' | 'rejected'


class ManualStoryCreate(BaseModel):
    video_url: str
    caption: Optional[str] = None
    scheduled_at: str       # "YYYY-MM-DD HH:MM:SS" hora Colombia
    template_code: Optional[str] = "behind_scenes_tienda"
    swipe_up_url: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
async def list_stories(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_admin_user),
):
    """Lista stories con filtro opcional por status."""
    where = "WHERE 1=1"
    params: dict = {"limit": limit}
    if status:
        where += " AND sp.status = :status"
        params["status"] = status

    rows = await db.execute(text(f"""
        SELECT sp.id, sp.post_type, sp.template_code, sp.creation_mode, sp.status,
               sp.video_url, sp.base_image_url, sp.caption, sp.swipe_up_url,
               sp.scheduled_at, sp.published_at, sp.expires_at,
               sp.instagram_story_id, sp.facebook_story_id,
               sp.dry_run, sp.image_cost_usd, sp.video_duration_sec,
               sp.video_size_bytes, sp.error_message,
               sp.created_at, sp.updated_at,
               st.name AS template_name, st.category AS template_category
        FROM content.story_posts sp
        LEFT JOIN content.story_templates st ON st.code = sp.template_code
        {where}
        ORDER BY sp.scheduled_at DESC
        LIMIT :limit
    """), params)
    stories = [dict(r._mapping) for r in rows.fetchall()]
    return {"stories": stories, "total": len(stories)}


@router.get("/templates")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_admin_user),
):
    rows = await db.execute(text("""
        SELECT id, code, name, category, audio_genre, has_swipe_up,
               swipe_up_destination, preferred_image_model,
               requires_real_product, requires_real_review, active
        FROM content.story_templates ORDER BY category, code
    """))
    return {"templates": [dict(r._mapping) for r in rows.fetchall()]}


@router.get("/config")
async def get_stories_config(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_admin_user),
):
    rows = await db.execute(text(
        "SELECT key, value, description FROM content.engine_config WHERE key LIKE 'stories%'"
    ))
    return {r.key: {"value": r.value, "description": r.description} for r in rows.fetchall()}


@router.patch("/config/{key}")
async def update_stories_config(
    key: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_admin_user),
):
    allowed = {"stories_active", "stories_dry_run_mode", "stories_per_day", "stories_fallback_enabled"}
    if key not in allowed:
        raise HTTPException(400, f"Clave no permitida: {key}")
    value = str(body.get("value", ""))
    await db.execute(text(
        "UPDATE content.engine_config SET value=:v, updated_at=NOW() WHERE key=:k"
    ), {"v": value, "k": key})
    await db.commit()
    return {"key": key, "value": value}


@router.get("/{story_id}")
async def get_story(
    story_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_admin_user),
):
    row = await db.execute(text("""
        SELECT sp.*, st.name AS template_name, st.category AS template_category
        FROM content.story_posts sp
        LEFT JOIN content.story_templates st ON st.code = sp.template_code
        WHERE sp.id = :id
    """), {"id": story_id})
    r = row.fetchone()
    if not r:
        raise HTTPException(404, "Story no encontrada")
    return dict(r._mapping)


@router.patch("/{story_id}/status")
async def update_story_status(
    story_id: str,
    body: StoryStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_admin_user),
):
    valid = {"approved", "rejected", "pending_approval"}
    if body.status not in valid:
        raise HTTPException(400, f"Status inválido: {body.status}")
    await db.execute(text("""
        UPDATE content.story_posts
        SET status=:s, updated_at=NOW()
        WHERE id=:id
    """), {"s": body.status, "id": story_id})
    await db.commit()
    return {"id": story_id, "status": body.status}


@router.post("/manual")
async def create_manual_story(
    body: ManualStoryCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_admin_user),
):
    """Crea story desde video subido manualmente (Modo B)."""
    from uuid import uuid4
    story_id = str(uuid4())
    await db.execute(text("""
        INSERT INTO content.story_posts
          (id, template_code, creation_mode, media_type, video_url,
           caption, swipe_up_url, status, dry_run, scheduled_at,
           expires_at, created_at, updated_at)
        VALUES
          (:id, :tc, 'manual_upload', 'video', :vu,
           :cap, :suu, 'pending_approval', false, :sa,
           :sa::timestamp + INTERVAL '24 hours', NOW(), NOW())
    """), {
        "id": story_id, "tc": body.template_code,
        "vu": body.video_url, "cap": body.caption,
        "suu": body.swipe_up_url, "sa": body.scheduled_at,
    })
    await db.commit()
    return {"id": story_id, "status": "pending_approval", "scheduled_at": body.scheduled_at}


@router.delete("/{story_id}")
async def delete_story(
    story_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_admin_user),
):
    row = await db.execute(text(
        "SELECT status FROM content.story_posts WHERE id=:id"
    ), {"id": story_id})
    r = row.fetchone()
    if not r:
        raise HTTPException(404, "Story no encontrada")
    if r.status == "published":
        raise HTTPException(400, "No se puede eliminar una story ya publicada")
    await db.execute(text("DELETE FROM content.story_posts WHERE id=:id"), {"id": story_id})
    await db.commit()
    return {"deleted": story_id}
