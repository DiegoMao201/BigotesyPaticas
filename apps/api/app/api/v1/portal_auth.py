"""Portal Auth — login por cédula + teléfono, sin contraseña."""
from __future__ import annotations

import re
import secrets
import unicodedata
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import and_, delete, select

from app.deps import DBSession
from app.models.crm import Customer
from app.models.portal import PortalSession

router = APIRouter(prefix="/portal/auth", tags=["portal"])

SESSION_TTL_DAYS = 30
_COOKIE = "bp_portal_token"
_REFERRAL_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


# ── helpers ──────────────────────────────────────────────────────────

def _generate_referral_code(full_name: str) -> str:
    """Genera un código de referido único tipo BP-NOM-XXX."""
    clean = unicodedata.normalize("NFKD", full_name or "USR").encode("ASCII", "ignore").decode()
    parts = clean.split()
    prefix_raw = parts[0][:3] if parts else "USR"
    initials = "".join(c for c in prefix_raw if c.isalpha())
    initials = (initials[:3] or "USR").upper().ljust(3, "X")
    suffix = "".join(secrets.choice(_REFERRAL_ALPHABET) for _ in range(3))
    return f"BP-{initials}-{suffix}"


def _normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone).lstrip("0")


def _phones_match(stored: str | None, entered: str) -> bool:
    if not stored:
        return False
    return _normalize_phone(stored) == _normalize_phone(entered)


async def _get_session(token: str, db: DBSession) -> PortalSession | None:
    now = datetime.now(UTC)
    row = (
        await db.execute(
            select(PortalSession).where(
                and_(PortalSession.token == token, PortalSession.expires_at > now)
            )
        )
    ).scalar_one_or_none()
    return row


async def get_portal_customer(
    db: DBSession,
    bp_portal_token: str | None = Cookie(default=None),
) -> Customer:
    if not bp_portal_token:
        raise HTTPException(status_code=401, detail="No autenticado")
    session = await _get_session(bp_portal_token, db)
    if not session:
        raise HTTPException(status_code=401, detail="Sesión expirada — vuelve a entrar")
    customer = (
        await db.execute(
            select(Customer).where(
                and_(Customer.id == session.customer_id, Customer.deleted_at == None)  # noqa: E711
            )
        )
    ).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=401, detail="Cliente no encontrado")
    return customer


PortalUser = Depends(get_portal_customer)


# ── schemas ───────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    document_id: str
    phone: str


class LoginResponse(BaseModel):
    status: str          # "existing" | "new"
    customer_id: str
    full_name: str | None
    has_pets: bool
    pet_name: str | None  # primer nombre desde extra si ya existe
    rfm_segment: str | None


class MeResponse(BaseModel):
    customer_id: str
    full_name: str
    document_id: str | None
    phone: str | None
    email: str | None
    address: str | None
    city: str | None
    rfm_segment: str | None
    rfm_monetary: float | None
    legacy_pet_name: str | None
    legacy_pet_type: str | None
    terms_accepted_at: str | None = None
    data_consent_at: str | None = None
    referral_code: str | None = None


class AcceptTermsRequest(BaseModel):
    terms: bool = True
    data_consent: bool = True
    version: str = "1.0"


# ── endpoints ─────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, response: Response, db: DBSession) -> LoginResponse:
    doc = payload.document_id.strip()
    phone = payload.phone.strip()

    # Buscar por cédula
    customer = (
        await db.execute(
            select(Customer).where(
                and_(Customer.document_id == doc, Customer.deleted_at == None)  # noqa: E711
            )
        )
    ).scalar_one_or_none()

    is_new = False

    if customer:
        # Verificar teléfono
        if not _phones_match(customer.phone, phone):
            raise HTTPException(
                status_code=401,
                detail="Teléfono no coincide con el registrado",
            )
    else:
        # Cliente nuevo — crear registro base
        is_new = True
        customer = Customer(
            full_name="",
            document_id=doc,
            phone=phone,
            extra={},
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)

    # Crear sesión
    token = secrets.token_urlsafe(48)
    expires = datetime.now(UTC) + timedelta(days=SESSION_TTL_DAYS)
    session = PortalSession(
        customer_id=customer.id,
        token=token,
        expires_at=expires,
    )
    db.add(session)
    await db.commit()

    # Limpiar sesiones viejas del mismo cliente (máx 5 activas)
    old_sessions = (
        await db.execute(
            select(PortalSession)
            .where(PortalSession.customer_id == customer.id)
            .order_by(PortalSession.created_at.desc())
            .offset(5)
        )
    ).scalars().all()
    for s in old_sessions:
        await db.delete(s)
    if old_sessions:
        await db.commit()

    response.set_cookie(
        key=_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL_DAYS * 86400,
        secure=True,
    )

    extra = customer.extra or {}
    return LoginResponse(
        status="new" if is_new else "existing",
        customer_id=str(customer.id),
        full_name=customer.full_name or None,
        has_pets=bool(extra.get("pet_name")),
        pet_name=extra.get("pet_name"),
        rfm_segment=customer.rfm_segment,
    )


@router.post("/logout")
async def logout(
    response: Response,
    db: DBSession,
    bp_portal_token: str | None = Cookie(default=None),
) -> dict:
    if bp_portal_token:
        await db.execute(
            delete(PortalSession).where(PortalSession.token == bp_portal_token)
        )
        await db.commit()
    response.delete_cookie(_COOKIE)
    return {"ok": True}


def _me_response(customer: Customer) -> MeResponse:
    extra = customer.extra or {}
    return MeResponse(
        customer_id=str(customer.id),
        full_name=customer.full_name,
        document_id=customer.document_id,
        phone=customer.phone,
        email=customer.email,
        address=customer.address,
        city=customer.city,
        rfm_segment=customer.rfm_segment,
        rfm_monetary=float(customer.rfm_monetary) if customer.rfm_monetary else None,
        legacy_pet_name=extra.get("pet_name"),
        legacy_pet_type=extra.get("pet_type"),
        terms_accepted_at=customer.terms_accepted_at.isoformat() if customer.terms_accepted_at else None,
        data_consent_at=customer.data_consent_at.isoformat() if customer.data_consent_at else None,
        referral_code=customer.referral_code,
    )


@router.get("/me", response_model=MeResponse)
async def me(db: DBSession, customer: Customer = PortalUser) -> MeResponse:
    # Auto-generar código de referido si no existe
    if not customer.referral_code:
        customer.referral_code = _generate_referral_code(customer.full_name or "")
        await db.commit()
        await db.refresh(customer)
    return _me_response(customer)


@router.get("/referral-code")
async def get_referral_code(db: DBSession, customer: Customer = PortalUser) -> dict:
    """Retorna el código de referido del cliente, generándolo si no existe."""
    if not customer.referral_code:
        customer.referral_code = _generate_referral_code(customer.full_name or "")
        await db.commit()
        await db.refresh(customer)
    return {"referral_code": customer.referral_code}


@router.patch("/me", response_model=MeResponse)
async def update_me(
    payload: dict,
    db: DBSession,
    customer: Customer = PortalUser,
) -> MeResponse:
    allowed = {"full_name", "email", "phone", "address", "city"}
    for k, v in payload.items():
        if k in allowed and v is not None:
            setattr(customer, k, v)
    await db.commit()
    await db.refresh(customer)
    return _me_response(customer)


@router.post("/me/accept-terms", response_model=MeResponse)
async def accept_terms(
    payload: AcceptTermsRequest,
    db: DBSession,
    customer: Customer = PortalUser,
) -> MeResponse:
    if not payload.terms or not payload.data_consent:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Debes aceptar los términos y el tratamiento de datos")
    now = datetime.now(UTC)
    customer.terms_accepted_at = now
    customer.data_consent_at = now
    customer.consent_version = payload.version
    await db.commit()
    await db.refresh(customer)
    return _me_response(customer)
