"""Landing pages SEO programáticas."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import DBSession

router = APIRouter(prefix="/landings", tags=["seo-landings"])


def _row(mapping) -> dict:
    d = dict(mapping)
    if isinstance(d.get("id"), UUID):
        d["id"] = str(d["id"])
    return d


class LandingOut(BaseModel):
    id: str
    slug: str
    target_keyword: str
    title: str
    h1: str
    meta_description: str | None
    intro_content: str | None
    category_slug: str | None
    geographic_focus: str | None
    cta_text: str | None
    is_active: bool
    ai_model: str | None

    class Config:
        from_attributes = True


class LandingCreate(BaseModel):
    slug: str
    target_keyword: str
    title: str
    h1: str
    meta_description: str | None = None
    intro_content: str | None = None
    category_slug: str | None = None
    geographic_focus: str | None = None
    cta_text: str | None = None
    is_active: bool = True
    ai_model: str | None = None


@router.get("", response_model=list[LandingOut])
async def list_landings(db: DBSession, active_only: bool = True):
    where = "WHERE is_active = true" if active_only else ""
    rows = await db.execute(
        text(f"SELECT * FROM content.seo_landings {where} ORDER BY created_at DESC")
    )
    return [_row(r._mapping) for r in rows]


@router.get("/{slug}", response_model=LandingOut)
async def get_landing(slug: str, db: DBSession):
    row = await db.execute(
        text("SELECT * FROM content.seo_landings WHERE slug = :slug AND is_active = true"),
        {"slug": slug},
    )
    result = row.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Landing not found")
    return _row(result._mapping)


@router.post("", response_model=LandingOut, status_code=201)
async def upsert_landing(data: LandingCreate, db: DBSession):
    params = data.model_dump()
    params["enriched_by_ai"] = data.ai_model is not None
    row = await db.execute(
        text("""
            INSERT INTO content.seo_landings
                (slug, target_keyword, title, h1, meta_description, intro_content,
                 category_slug, geographic_focus, cta_text, is_active, enriched_by_ai, ai_model,
                 updated_at)
            VALUES
                (:slug, :target_keyword, :title, :h1, :meta_description, :intro_content,
                 :category_slug, :geographic_focus, :cta_text, :is_active,
                 :enriched_by_ai, :ai_model, now())
            ON CONFLICT (slug) DO UPDATE SET
                target_keyword  = EXCLUDED.target_keyword,
                title           = EXCLUDED.title,
                h1              = EXCLUDED.h1,
                meta_description = EXCLUDED.meta_description,
                intro_content   = EXCLUDED.intro_content,
                category_slug   = EXCLUDED.category_slug,
                geographic_focus = EXCLUDED.geographic_focus,
                cta_text        = EXCLUDED.cta_text,
                is_active       = EXCLUDED.is_active,
                enriched_by_ai  = EXCLUDED.enriched_by_ai,
                ai_model        = EXCLUDED.ai_model,
                updated_at      = now()
            RETURNING *
        """),
        params,
    )
    await db.commit()
    return _row(row.fetchone()._mapping)
