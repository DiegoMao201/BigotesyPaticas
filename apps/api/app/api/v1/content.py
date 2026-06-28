"""Sprint 6A — Content Engine API.

Endpoints admin para generar, revisar, editar, aprobar y publicar posts en
Instagram y Facebook usando IA (GPT-image-1 + Claude Haiku 4.5).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.sql import text

from app.deps import DBSession, require_permission

router = APIRouter(
    prefix="/v1/admin/content",
    tags=["content-engine"],
    dependencies=[Depends(require_permission("admin"))],
)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class GeneratePostRequest(BaseModel):
    template_code: str
    context: dict
    scheduled_at: datetime | None = None


class EditPostRequest(BaseModel):
    caption: str | None = None
    hashtags: list[str] | None = None
    scheduled_at: datetime | None = None
    target_platforms: list[str] | None = None
    visual_prompt: str | None = None


class RejectRequest(BaseModel):
    reason: str | None = None


class RegenerateImageRequest(BaseModel):
    visual_prompt: str | None = None


class EngineConfigUpdate(BaseModel):
    key: str
    value: str


class TestPublishRequest(BaseModel):
    post_id: uuid.UUID
    target: Literal["instagram", "facebook"]


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_post_or_404(db: DBSession, post_id: uuid.UUID) -> dict:
    row = (await db.execute(
        text("SELECT * FROM content.scheduled_posts WHERE id = :id"),
        {"id": str(post_id)},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    return dict(row)


async def _get_template_or_404(db: DBSession, code: str) -> dict:
    row = (await db.execute(
        text("SELECT * FROM content.post_templates WHERE code = :code AND active = true"),
        {"code": code},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Template '{code}' no encontrado o inactivo")
    return dict(row)


async def _get_next_scheduled_at(db: DBSession, preferred_at: datetime | None) -> datetime:
    """Elige el próximo slot horario disponible."""
    if preferred_at:
        return preferred_at
    now = datetime.now(UTC)
    dow = now.weekday()  # 0=Mon
    # Convertir a formato BD (0=Dom)
    bd_dow = (dow + 1) % 7
    slot = (await db.execute(
        text("""
            SELECT hour, minute FROM content.optimal_time_slots
            WHERE day_of_week = :dow
            ORDER BY hour, minute
            LIMIT 1
        """),
        {"dow": bd_dow},
    )).first()
    if slot:
        return now.replace(hour=slot[0], minute=slot[1], second=0, microsecond=0)
    return now


def _post_to_dict(row: dict) -> dict:
    """Serializa un row de scheduled_posts a dict JSON-safe."""
    result = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            result[k] = str(v)
        else:
            result[k] = v
    return result


# ─── 4.1 Generar post ─────────────────────────────────────────────────────────

@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_post(payload: GeneratePostRequest, db: DBSession):
    """Genera un post IA y lo inserta con status pending_approval."""
    from app.services.content_generator import ContentGenerator

    # Verificar kill-switch
    cfg = (await db.execute(
        text("SELECT value FROM content.engine_config WHERE key = 'is_active'")
    )).scalar_one_or_none()
    if cfg == "false":
        raise HTTPException(
            status_code=503,
            detail="Content engine desactivado (kill-switch). Activar en /engine-config.",
        )

    template = await _get_template_or_404(db, payload.template_code)
    gen = ContentGenerator()
    try:
        result = await gen.generate_post(template, payload.context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando post: {e}")

    scheduled_at = await _get_next_scheduled_at(db, payload.scheduled_at)

    import json as _json
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    # asyncpg no admite ::jsonb en text() — usar CAST con nombre distinto
    row = (await db.execute(
        text("""
            INSERT INTO content.scheduled_posts
                (template_id, category, source_data, visual_prompt, caption,
                 hashtags, cta_url, image_url, image_local_path, scheduled_at,
                 status, dry_run)
            VALUES
                (:tpl_id, :category, CAST(:src_data AS jsonb), :visual_prompt, :caption,
                 :hashtags, :cta_url, :image_url, :image_local_path, :scheduled_at,
                 'pending_approval', false)
            RETURNING *
        """),
        {
            "tpl_id":          str(template["id"]),
            "category":        template["category"],
            "src_data":        _json.dumps(payload.context),
            "visual_prompt":   result["visual_prompt"],
            "caption":         result["caption"],
            "hashtags":        result.get("hashtags", []),
            "cta_url":         result.get("cta_url"),
            "image_url":       result.get("image_url"),
            "image_local_path":result.get("image_local_path"),
            "scheduled_at":    scheduled_at,
        },
    )).mappings().first()
    await db.commit()
    return _post_to_dict(dict(row))


# ─── 4.2 Listar posts ────────────────────────────────────────────────────────

@router.get("/scheduled-posts")
async def list_posts(
    db: DBSession,
    status_filter: str = Query("pending_approval", alias="status"),
    page: int = 1,
    page_size: int = 20,
    category: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    page_size = min(page_size, 100)
    conditions = []
    params: dict = {}

    if status_filter != "all":
        conditions.append("status = :status")
        params["status"] = status_filter
    if category:
        conditions.append("category = :category")
        params["category"] = category
    if date_from:
        conditions.append("scheduled_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("scheduled_at <= :date_to")
        params["date_to"] = date_to

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * page_size
    params.update({"limit": page_size, "offset": offset})

    total = (await db.execute(
        text(f"SELECT COUNT(*) FROM content.scheduled_posts {where}"), params
    )).scalar_one()

    rows = (await db.execute(
        text(f"""
            SELECT * FROM content.scheduled_posts
            {where}
            ORDER BY scheduled_at ASC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )).mappings().all()

    return {
        "items": [_post_to_dict(dict(r)) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ─── 4.3 Obtener un post ─────────────────────────────────────────────────────

@router.get("/scheduled-posts/{post_id}")
async def get_post(post_id: uuid.UUID, db: DBSession):
    return _post_to_dict(await _get_post_or_404(db, post_id))


# ─── 4.4 Editar post ─────────────────────────────────────────────────────────

@router.patch("/scheduled-posts/{post_id}")
async def edit_post(post_id: uuid.UUID, payload: EditPostRequest, db: DBSession):
    post = await _get_post_or_404(db, post_id)
    updates: dict = {"edited_by_admin": True, "updated_at": datetime.now(UTC)}
    if payload.caption is not None:
        updates["caption"] = payload.caption
    if payload.hashtags is not None:
        updates["hashtags"] = payload.hashtags
    if payload.scheduled_at is not None:
        updates["scheduled_at"] = payload.scheduled_at
    if payload.target_platforms is not None:
        updates["target_platforms"] = payload.target_platforms
    if payload.visual_prompt is not None:
        updates["visual_prompt"] = payload.visual_prompt

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["post_id"] = str(post_id)
    await db.execute(
        text(f"UPDATE content.scheduled_posts SET {set_clause} WHERE id = :post_id"),
        updates,
    )
    await db.commit()
    return _post_to_dict(await _get_post_or_404(db, post_id))


# ─── 4.5 Regenerar imagen ────────────────────────────────────────────────────

@router.post("/scheduled-posts/{post_id}/regenerate-image")
async def regenerate_image(post_id: uuid.UUID, payload: RegenerateImageRequest, db: DBSession):
    from app.services.content_generator import ContentGenerator

    post = await _get_post_or_404(db, post_id)
    prompt = payload.visual_prompt or post["visual_prompt"]

    gen = ContentGenerator()
    try:
        cdn_url, local_path = await gen.regenerate_image(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error regenerando imagen: {e}")

    await db.execute(
        text("""
            UPDATE content.scheduled_posts
            SET image_url = :url, image_local_path = :lp,
                visual_prompt = :vp, updated_at = :now
            WHERE id = :id
        """),
        {"url": cdn_url, "lp": local_path, "vp": prompt, "now": datetime.now(UTC), "id": str(post_id)},
    )
    await db.commit()
    return {"ok": True, "image_url": cdn_url}


# ─── 4.6 Aprobar post ────────────────────────────────────────────────────────

@router.post("/scheduled-posts/{post_id}/approve")
async def approve_post(post_id: uuid.UUID, db: DBSession):
    await _get_post_or_404(db, post_id)
    now = datetime.now(UTC)
    await db.execute(
        text("""
            UPDATE content.scheduled_posts
            SET status = 'approved', approved_at = :now, updated_at = :now
            WHERE id = :id
        """),
        {"now": now, "id": str(post_id)},
    )
    await db.commit()
    return {"ok": True, "status": "approved"}


# ─── 4.7 Rechazar post ────────────────────────────────────────────────────────

@router.post("/scheduled-posts/{post_id}/reject")
async def reject_post(post_id: uuid.UUID, payload: RejectRequest, db: DBSession):
    await _get_post_or_404(db, post_id)
    await db.execute(
        text("""
            UPDATE content.scheduled_posts
            SET status = 'rejected', rejected_reason = :reason, updated_at = :now
            WHERE id = :id
        """),
        {"reason": payload.reason, "now": datetime.now(UTC), "id": str(post_id)},
    )
    await db.commit()
    return {"ok": True, "status": "rejected"}


# ─── 4.8 Test publish ────────────────────────────────────────────────────────

@router.post("/test-publish")
async def test_publish(payload: TestPublishRequest, db: DBSession):
    """Prueba publicar un post en Meta (respeta dry_run_mode de engine_config)."""
    post = await _get_post_or_404(db, payload.post_id)

    dry = (await db.execute(
        text("SELECT value FROM content.engine_config WHERE key = 'dry_run_mode'")
    )).scalar_one_or_none()

    if dry == "true":
        return {
            "ok": True,
            "dry_run": True,
            "message": "dry_run_mode=true — Meta API NO fue contactada",
            "target": payload.target,
        }

    from app.services.meta_publisher import publish_to_meta
    try:
        result = await publish_to_meta(post, payload.target, dry_run=False)
        return {"ok": True, "dry_run": False, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── 4.9 Leer engine config ───────────────────────────────────────────────────

@router.get("/engine-config")
async def get_engine_config(db: DBSession):
    rows = (await db.execute(
        text("SELECT key, value, description FROM content.engine_config ORDER BY key")
    )).mappings().all()
    return {r["key"]: {"value": r["value"], "description": r["description"]} for r in rows}


# ─── 4.10 Actualizar engine config ──────────────────────────────────────────

@router.patch("/engine-config")
async def update_engine_config(payload: EngineConfigUpdate, db: DBSession):
    await db.execute(
        text("""
            UPDATE content.engine_config
            SET value = :value, updated_at = NOW()
            WHERE key = :key
        """),
        {"key": payload.key, "value": payload.value},
    )
    await db.commit()
    return {"ok": True, "key": payload.key, "value": payload.value}


# ─── Utilidades adicionales ───────────────────────────────────────────────────

@router.get("/templates")
async def list_templates(db: DBSession):
    rows = (await db.execute(
        text("SELECT id, code, name, category, visual_style, cta_type, active FROM content.post_templates ORDER BY category, name")
    )).mappings().all()
    return [dict(r) for r in rows]


@router.post("/generate-week-plan")
async def trigger_week_plan(db: DBSession):
    """Fuerza ejecución del job de planificación semanal."""
    import asyncio, subprocess, sys
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "/app/scripts/plan_content_week.py",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        return {
            "ok": proc.returncode == 0,
            "output": (stdout or b"").decode()[-3000:],
            "error": (stderr or b"").decode()[-500:] if proc.returncode != 0 else None,
        }
    except asyncio.TimeoutError:
        proc.kill()
        return {"ok": False, "error": "timeout (5 minutos)"}


@router.post("/approve-all-pending")
async def approve_all_pending(db: DBSession):
    now = datetime.now(UTC)
    result = await db.execute(
        text("""
            UPDATE content.scheduled_posts
            SET status = 'approved', approved_at = :now, updated_at = :now
            WHERE status = 'pending_approval'
        """),
        {"now": now},
    )
    await db.commit()
    return {"ok": True, "approved": result.rowcount}
