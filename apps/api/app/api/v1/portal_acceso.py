"""Acceso moderno al portal/app (8-nov-2026): huella o Face ID (passkeys) y Google.

Diego: "que el cliente pueda loguearse con Google… con Face ID o la huella del celular".
Hasta hoy el único acceso era cédula + teléfono: dos datos que cualquiera puede saber de
otra persona. Los passkeys los guarda el celular, no salen de él y no se pueden adivinar:
son a la vez lo más cómodo y lo más seguro. Google sirve para entrar sin escribir nada.

Decisiones:
  · Sin tablas nuevas: las llaves y el vínculo con Google viven en `customers.extra`
    (`passkeys` = lista, `google_sub`). Cero migraciones, cero riesgo para alembic.
  · El reto de WebAuthn va firmado (HMAC con JWT_SECRET) y vuelve con el cliente; así
    funciona aunque la API corra en varios procesos, sin guardar estado.
  · La primera vez con Google se pide cédula + teléfono UNA vez para unir la cuenta de
    Google con el cliente de la tienda (la cédula es la llave de facturas y puntos).
"""
from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import UTC, datetime, timedelta
import secrets

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import and_, select

from app.api.v1.portal_auth import (
    SESSION_TTL_DAYS,
    _COOKIE,
    PortalUser,
    _phones_match,
)
from app.config import get_settings
from app.deps import DBSession
from app.models.crm import Customer
from app.models.portal import PortalSession

router = APIRouter(prefix="/portal/auth", tags=["portal"])

RP_ID = os.getenv("PASSKEY_RP_ID", "bigotesypaticas.com")
RP_NAME = "Bigotes y Paticas"
ORIGENES = [o.strip() for o in os.getenv(
    "PASSKEY_ORIGINS", "https://mi.bigotesypaticas.com,https://bigotesypaticas.com"
).split(",") if o.strip()]
# Android: dentro de la app (TWA) el origen sigue siendo https://mi.bigotesypaticas.com.
GOOGLE_CLIENT_IDS = [c.strip() for c in os.getenv("GOOGLE_OAUTH_CLIENT_IDS", "").split(",") if c.strip()]


# ── firma de estados (reto, vínculo con Google) ────────────────────────
def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _firmar(datos: dict, ttl: int = 300) -> str:
    datos = {**datos, "exp": int(time.time()) + ttl}
    cuerpo = _b64(json.dumps(datos, separators=(",", ":")).encode())
    firma = _b64(hmac.new(get_settings().jwt_secret.encode(), cuerpo.encode(), hashlib.sha256).digest())
    return f"{cuerpo}.{firma}"


def _leer(token: str) -> dict:
    try:
        cuerpo, firma = token.split(".", 1)
        esperada = _b64(hmac.new(get_settings().jwt_secret.encode(), cuerpo.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(firma, esperada):
            raise ValueError
        datos = json.loads(_unb64(cuerpo))
        if datos.get("exp", 0) < time.time():
            raise ValueError
        return datos
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="La solicitud venció. Intenta de nuevo.")


COOKIE_EQUIPO = "bp_equipo"
EQUIPO_DIAS = 180


def marcar_equipo(response: Response, c: Customer) -> None:
    """Celular de confianza: aquí ya se probó quién es; no se vuelve a pedir código (180 días)."""
    response.set_cookie(
        key=COOKIE_EQUIPO, value=_firmar({"t": "eq", "u": str(c.id)}, ttl=EQUIPO_DIAS * 86400),
        httponly=True, samesite="lax", secure=True, max_age=EQUIPO_DIAS * 86400,
    )


async def _emitir_sesion(db, response: Response, customer: Customer) -> dict:
    marcar_equipo(response, customer)
    token = secrets.token_urlsafe(48)
    db.add(PortalSession(customer_id=customer.id, token=token,
                         expires_at=datetime.now(UTC) + timedelta(days=SESSION_TTL_DAYS)))
    await db.commit()
    response.set_cookie(key=_COOKIE, value=token, httponly=True, samesite="lax",
                        max_age=SESSION_TTL_DAYS * 86400, secure=True)
    extra = customer.extra or {}
    return {
        "status": "existing" if customer.full_name else "new",
        "customer_id": str(customer.id),
        "full_name": customer.full_name or None,
        "has_pets": bool(extra.get("pet_name")),
        "pet_name": extra.get("pet_name"),
        "rfm_segment": customer.rfm_segment,
    }


def _activo(c: Customer | None) -> bool:
    return bool(c) and c.deleted_at is None and not (c.extra or {}).get("eliminacion")


# ── PASSKEYS (huella / Face ID) ────────────────────────────────────────
class VerificarIn(BaseModel):
    credential: dict
    state: str
    nombre: str | None = None


@router.post("/passkey/register/options")
async def passkey_registro_opciones(customer: Customer = PortalUser) -> dict:
    from webauthn import generate_registration_options, options_to_json
    from webauthn.helpers.structs import (
        AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor,
        ResidentKeyRequirement, UserVerificationRequirement,
    )

    ya = [PublicKeyCredentialDescriptor(id=_unb64(p["id"])) for p in (customer.extra or {}).get("passkeys", [])]
    opts = generate_registration_options(
        rp_id=RP_ID, rp_name=RP_NAME,
        user_id=customer.id.bytes,
        user_name=customer.phone or customer.document_id or str(customer.id),
        user_display_name=customer.full_name or "Cliente Bigotes y Paticas",
        exclude_credentials=ya,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )
    return {"options": json.loads(options_to_json(opts)),
            "state": _firmar({"c": _b64(opts.challenge), "u": str(customer.id), "t": "reg"})}


@router.post("/passkey/register/verify")
async def passkey_registro_verificar(payload: VerificarIn, db: DBSession, customer: Customer = PortalUser) -> dict:
    from webauthn import verify_registration_response

    st = _leer(payload.state)
    if st.get("t") != "reg" or st.get("u") != str(customer.id):
        raise HTTPException(status_code=400, detail="Solicitud inválida")
    try:
        v = verify_registration_response(
            credential=payload.credential, expected_challenge=_unb64(st["c"]),
            expected_origin=ORIGENES, expected_rp_id=RP_ID, require_user_verification=True,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"No se pudo registrar: {e}") from e
    extra = dict(customer.extra or {})
    llaves = list(extra.get("passkeys", []))
    llaves.append({
        "id": _b64(v.credential_id), "pk": _b64(v.credential_public_key), "n": v.sign_count,
        "nombre": (payload.nombre or "Este celular")[:60], "creada": datetime.now(UTC).isoformat(),
    })
    extra["passkeys"] = llaves[-10:]
    customer.extra = extra
    await db.commit()
    return {"ok": True, "total": len(extra["passkeys"])}


@router.post("/passkey/login/options")
async def passkey_login_opciones() -> dict:
    from webauthn import generate_authentication_options, options_to_json
    from webauthn.helpers.structs import UserVerificationRequirement

    opts = generate_authentication_options(rp_id=RP_ID, user_verification=UserVerificationRequirement.REQUIRED)
    return {"options": json.loads(options_to_json(opts)), "state": _firmar({"c": _b64(opts.challenge), "t": "auth"})}


@router.post("/passkey/login/verify")
async def passkey_login_verificar(payload: VerificarIn, response: Response, db: DBSession) -> dict:
    from webauthn import verify_authentication_response

    st = _leer(payload.state)
    if st.get("t") != "auth":
        raise HTTPException(status_code=400, detail="Solicitud inválida")
    handle = (payload.credential.get("response") or {}).get("userHandle")
    cred_id = payload.credential.get("id") or payload.credential.get("rawId")
    if not handle or not cred_id:
        raise HTTPException(status_code=400, detail="Esta llave no sirve para entrar")
    try:
        cid = uuid.UUID(bytes=_unb64(handle))
    except ValueError:
        raise HTTPException(status_code=400, detail="Esta llave no sirve para entrar")
    customer = (await db.execute(select(Customer).where(Customer.id == cid))).scalar_one_or_none()
    if not _activo(customer):
        raise HTTPException(status_code=401, detail="No encontramos tu cuenta")
    extra = copy.deepcopy(customer.extra or {})
    llaves = list(extra.get("passkeys", []))
    llave = next((p for p in llaves if p["id"] == cred_id), None)
    if not llave:
        raise HTTPException(status_code=401, detail="Esta huella ya no está registrada. Entra con tu cédula.")
    try:
        v = verify_authentication_response(
            credential=payload.credential, expected_challenge=_unb64(st["c"]),
            expected_origin=ORIGENES, expected_rp_id=RP_ID,
            credential_public_key=_unb64(llave["pk"]), credential_current_sign_count=llave.get("n", 0),
            require_user_verification=True,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="No pudimos verificar tu huella") from e
    llave["n"] = v.new_sign_count
    llave["usada"] = datetime.now(UTC).isoformat()
    extra["passkeys"] = llaves
    customer.extra = extra
    return await _emitir_sesion(db, response, customer)


@router.get("/passkeys")
async def mis_passkeys(customer: Customer = PortalUser) -> list[dict]:
    return [{"id": p["id"], "nombre": p.get("nombre"), "creada": p.get("creada"), "usada": p.get("usada")}
            for p in (customer.extra or {}).get("passkeys", [])]


@router.delete("/passkeys/{pid}")
async def borrar_passkey(pid: str, db: DBSession, customer: Customer = PortalUser) -> dict:
    extra = dict(customer.extra or {})
    extra["passkeys"] = [p for p in extra.get("passkeys", []) if p["id"] != pid]
    customer.extra = extra
    await db.commit()
    return {"ok": True}


# ── GOOGLE ─────────────────────────────────────────────────────────────
class GoogleIn(BaseModel):
    credential: str


class GoogleLinkIn(BaseModel):
    link_token: str
    document_id: str
    phone: str


@router.get("/google/config")
async def google_config() -> dict:
    """El portal muestra el botón de Google solo si hay un client ID configurado."""
    return {"client_id": GOOGLE_CLIENT_IDS[0] if GOOGLE_CLIENT_IDS else None}


@router.post("/google")
async def google_login(payload: GoogleIn, response: Response, db: DBSession) -> dict:
    if not GOOGLE_CLIENT_IDS:
        raise HTTPException(status_code=503, detail="Entrar con Google aún no está activo")
    from google.auth.transport import requests as greq
    from google.oauth2 import id_token

    try:
        info = id_token.verify_oauth2_token(payload.credential, greq.Request())
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Google no confirmó tu cuenta") from e
    if info.get("aud") not in GOOGLE_CLIENT_IDS or info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise HTTPException(status_code=401, detail="Google no confirmó tu cuenta")
    sub, email = info["sub"], (info.get("email") or "").lower()

    c = (await db.execute(select(Customer).where(Customer.extra["google_sub"].astext == sub))).scalar_one_or_none()
    if c is None and email and info.get("email_verified"):
        por_correo = (await db.execute(select(Customer).where(
            and_(Customer.email == email, Customer.deleted_at == None)))).scalars().all()  # noqa: E711
        if len(por_correo) == 1:
            c = por_correo[0]
            extra = dict(c.extra or {}); extra["google_sub"] = sub; c.extra = extra
    if c is not None:
        if not _activo(c):
            raise HTTPException(status_code=403, detail="Esta cuenta se cerró porque pediste eliminarla.")
        return await _emitir_sesion(db, response, c)
    # Primera vez: unir con la cédula (llave de facturas y puntos), una sola vez.
    return {"status": "link_required",
            "link_token": _firmar({"t": "g", "sub": sub, "email": email, "name": info.get("name", "")}, ttl=900),
            "email": email, "name": info.get("name")}


@router.post("/google/link")
async def google_unir(payload: GoogleLinkIn, request: Request, response: Response, db: DBSession) -> dict:
    from app.api.v1.portal_codigo import bloqueo_cedula, frenar_ip, paso_seguro, sumar_fallo, telefono_no_coincide

    frenar_ip(request)
    st = _leer(payload.link_token)
    if st.get("t") != "g":
        raise HTTPException(status_code=400, detail="Solicitud inválida")
    doc, tel = payload.document_id.strip(), payload.phone.strip()
    correo_g = (st.get("email") or "").lower()
    c = (await db.execute(select(Customer).where(
        and_(Customer.document_id == doc, Customer.deleted_at == None)))).scalar_one_or_none()  # noqa: E711
    if c is not None:
        if not _activo(c):
            raise HTTPException(status_code=403, detail="Esta cuenta se cerró porque pediste eliminarla.")
        bloqueo_cedula(c)
        if not _phones_match(c.phone, tel):
            sumar_fallo(c)
            await db.commit()
            raise HTTPException(status_code=401, detail=telefono_no_coincide(c))
        # 8-nov-2026: si la cuenta ya tiene OTRO correo, Google no basta: se manda código a
        # ese correo (si no, cualquiera con la cédula y el teléfono uniría su propio Google).
        if c.email and c.email.lower() != correo_g:
            return await paso_seguro(db, request, response, c, None, {"gsub": st["sub"]})
    else:
        c = Customer(full_name=st.get("name") or "", document_id=doc, phone=tel, extra={})
        db.add(c)
        await db.flush()
    extra = dict(c.extra or {}); extra["google_sub"] = st["sub"]
    if correo_g:
        if not c.email:
            c.email = correo_g
        extra["correo_verificado"] = correo_g  # Google ya verificó ese correo
    extra.pop("acceso_fallos", None)
    c.extra = extra
    return await _emitir_sesion(db, response, c)
