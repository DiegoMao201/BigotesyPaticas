"""Autenticación de aliados — registro público, login, refresh, perfil propio.

JWT separado del de admin/portal: los tokens de aliado llevan `scope: "partner"`
(claim propio, no "aud" — ese es reservado y jose lo valida contra una audiencia
esperada si está presente, lo cual rompía el decode sin ese parámetro extra).
y el `sub` es el id de `PartnerUser` (no de `Partner`). El registro público
crea el `Partner` (negocio) con `published_at = NULL` — queda pendiente de
aprobación por el staff de BP antes de aparecer en el directorio.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from slugify import slugify
from sqlalchemy import select

from app.config import get_settings
from app.deps import DBSession
from app.models.partners import Partner, PartnerUser
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/partner/auth", tags=["partner"])
settings = get_settings()

PARTNER_TYPES = {"vet", "walker", "shelter", "groomer"}

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/partner/auth/login", auto_error=False)


# ── schemas ───────────────────────────────────────────────────────────


class PartnerRegisterIn(BaseModel):
    partner_type: str
    business_name: str = Field(min_length=2, max_length=160)
    legal_name: str = Field(min_length=2, max_length=160)
    document_id: str = Field(min_length=3, max_length=30)
    city: str = Field(min_length=2, max_length=80)
    address: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    bio: str | None = None
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)


class PartnerLoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class PartnerOut(BaseModel):
    id: str
    slug: str
    partner_type: str
    business_name: str
    city: str
    is_published: bool
    is_verified: bool


class PartnerUserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    partner: PartnerOut


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    partner_user: PartnerUserOut


def _partner_out(p: Partner) -> PartnerOut:
    return PartnerOut(
        id=str(p.id),
        slug=p.slug,
        partner_type=p.partner_type,
        business_name=p.business_name,
        city=p.city,
        is_published=p.published_at is not None,
        is_verified=p.verified_at is not None,
    )


def _partner_user_out(pu: PartnerUser, p: Partner) -> PartnerUserOut:
    return PartnerUserOut(
        id=str(pu.id),
        email=str(pu.email),
        full_name=pu.full_name,
        role=pu.role,
        partner=_partner_out(p),
    )


async def _unique_slug(db: DBSession, name: str) -> str:
    base = slugify(name)
    slug = base
    suffix = 2
    while (await db.execute(select(Partner.id).where(Partner.slug == slug))).scalar_one_or_none():
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


# ── dependency: usuario de aliado autenticado ───────────────────────────


async def get_current_partner_user(
    token: Annotated[str | None, Depends(_oauth2_scheme)],
    db: DBSession,
) -> PartnerUser:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token requerido")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access" or payload.get("scope") != "partner":
            raise ValueError("Token inválido")
        partner_user_id = payload["sub"]
    except (ValueError, KeyError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    pu = (
        await db.execute(select(PartnerUser).where(PartnerUser.id == partner_user_id))
    ).scalar_one_or_none()
    if pu is None or not pu.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Cuenta inválida")
    return pu


CurrentPartnerUser = Annotated[PartnerUser, Depends(get_current_partner_user)]


def _mint_tokens(partner_user_id: uuid.UUID) -> tuple[str, str]:
    access = create_access_token(partner_user_id, extra_claims={"scope": "partner"})
    refresh = create_refresh_token(partner_user_id, extra_claims={"scope": "partner"})
    return access, refresh


# ── endpoints ─────────────────────────────────────────────────────────


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(payload: PartnerRegisterIn, db: DBSession) -> TokenOut:
    if payload.partner_type not in PARTNER_TYPES:
        raise HTTPException(
            422, f"partner_type debe ser uno de: {', '.join(sorted(PARTNER_TYPES))}"
        )

    existing = (
        await db.execute(select(PartnerUser).where(PartnerUser.email == payload.email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese correo")

    slug = await _unique_slug(db, payload.business_name)

    partner = Partner(
        slug=slug,
        partner_type=payload.partner_type,
        business_name=payload.business_name,
        legal_name=payload.legal_name,
        document_id=payload.document_id,
        email=payload.email,
        phone=payload.phone,
        whatsapp=payload.whatsapp or payload.phone,
        address=payload.address,
        city=payload.city,
        lat=payload.lat,
        lng=payload.lng,
        bio=payload.bio,
        published_at=None,
        verified_at=None,
    )
    db.add(partner)
    await db.flush()

    partner_user = PartnerUser(
        partner_id=partner.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="owner",
        full_name=payload.full_name,
    )
    db.add(partner_user)
    await db.commit()
    await db.refresh(partner_user)
    await db.refresh(partner)

    access, refresh = _mint_tokens(partner_user.id)
    return TokenOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        partner_user=_partner_user_out(partner_user, partner),
    )


@router.post("/login", response_model=TokenOut)
async def login(payload: PartnerLoginIn, db: DBSession) -> TokenOut:
    pu = (
        await db.execute(select(PartnerUser).where(PartnerUser.email == payload.email))
    ).scalar_one_or_none()
    if pu is None or not pu.is_active or not verify_password(payload.password, pu.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")

    partner = (await db.execute(select(Partner).where(Partner.id == pu.partner_id))).scalar_one()

    access, refresh = _mint_tokens(pu.id)
    return TokenOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        partner_user=_partner_user_out(pu, partner),
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh(payload: RefreshIn, db: DBSession) -> TokenOut:
    try:
        claims = decode_token(payload.refresh_token)
        if claims.get("type") != "refresh" or claims.get("scope") != "partner":
            raise ValueError("Token inválido")
        partner_user_id = claims["sub"]
    except (ValueError, KeyError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    pu = (
        await db.execute(select(PartnerUser).where(PartnerUser.id == partner_user_id))
    ).scalar_one_or_none()
    if pu is None or not pu.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Cuenta inválida")

    partner = (await db.execute(select(Partner).where(Partner.id == pu.partner_id))).scalar_one()
    access, refresh_tok = _mint_tokens(pu.id)
    return TokenOut(
        access_token=access,
        refresh_token=refresh_tok,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        partner_user=_partner_user_out(pu, partner),
    )


@router.get("/me", response_model=PartnerUserOut)
async def me(partner_user: CurrentPartnerUser, db: DBSession) -> PartnerUserOut:
    partner = (
        await db.execute(select(Partner).where(Partner.id == partner_user.partner_id))
    ).scalar_one()
    return _partner_user_out(partner_user, partner)
