"""Landing pages SEO programáticas."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(prefix="/landings", tags=["seo-landings"])


class LandingOut(BaseModel):
    id: str
    slug: str
    target_keyword: str
    title: str
    h1: str
    meta_description: Optional[str]
    intro_content: Optional[str]
    category_slug: Optional[str]
    geographic_focus: Optional[str]
    cta_text: Optional[str]
    is_active: bool
    ai_model: Optional[str]

    class Config:
        from_attributes = True


class LandingCreate(BaseModel):
    slug: str
    target_keyword: str
    title: str
    h1: str
    meta_description: Optional[str] = None
    intro_content: Optional[str] = None
    category_slug: Optional[str] = None
    geographic_focus: Optional[str] = None
    cta_text: Optional[str] = None
    is_active: bool = True
    ai_model: Optional[str] = None


@router.get("", response_model=list[LandingOut])
async def list_landings(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    where = "WHERE is_active = true" if active_only else ""
    rows = await db.execute(
        text(f"SELECT * FROM content.seo_landings {where} ORDER BY created_at DESC")
    )
    return [dict(r._mapping) for r in rows]


@router.get("/{slug}", response_model=LandingOut)
async def get_landing(slug: str, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text("SELECT * FROM content.seo_landings WHERE slug = :slug AND is_active = true"),
        {"slug": slug},
    )
    result = row.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Landing not found")
    return dict(result._mapping)


@router.post("", response_model=LandingOut, status_code=201)
async def upsert_landing(data: LandingCreate, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text("""
            INSERT INTO content.seo_landings
                (slug, target_keyword, title, h1, meta_description, intro_content,
                 category_slug, geographic_focus, cta_text, is_active, enriched_by_ai, ai_model,
                 updated_at)
            VALUES
                (:slug, :target_keyword, :title, :h1, :meta_description, :intro_content,
                 :category_slug, :geographic_focus, :cta_text, :is_active,
                 :ai_model IS NOT NULL, :ai_model, now())
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
        data.model_dump(),
    )
    await db.commit()
    return dict(row.fetchone()._mapping)
