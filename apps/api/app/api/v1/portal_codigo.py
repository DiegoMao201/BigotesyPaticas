"""Código al correo para entrar con cédula + teléfono (8-nov-2026).

Diego: "que les pida iniciar con Google o que registren un correo para enviarles el
código, porque hay clientes que están ingresando". Hasta hoy bastaba saber la cédula y
el teléfono de alguien para entrar a su cuenta, y no había límite de intentos.

Reglas:
  · Cédula + teléfono correctos YA NO abren la sesión en un celular nuevo: se manda un
    código de 6 dígitos al correo del cliente. En el celular donde ya se verificó queda
    una cookie firmada (`bp_equipo`, 180 días) y no se vuelve a pedir.
  · Si el cliente no tiene correo (776 de 801 el 8-nov), se le pide uno y el código va
    ahí; al verificarlo queda guardado. Si el correo ya es de otra cuenta, no se acepta.
  · La huella/Face ID y Google no pasan por aquí: ya prueban quién es la persona.
  · Topes: 5 teléfonos equivocados por cédula en 15 min, 5 códigos fallidos por envío,
    5 envíos por hora. Todo vive en `customers.extra` (la API corre en 4 procesos, así
    que nada se guarda en memoria salvo el tope por IP, que es solo un freno extra).
  · La cuenta del revisor de Google Play (cédula de prueba) no pide código: no tiene
    correo al que llegue y no tiene datos reales.

Límite conocido: quien sepa la cédula y el teléfono de un cliente SIN correo puede
registrar su propio correo la primera vez. Es el mismo riesgo de antes, pero solo una
vez por cuenta y queda en el log; cerrarlo del todo exige un canal que solo tenga el
cliente (un SMS o WhatsApp), y el número de WhatsApp no se toca.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import html
import logging
import os
import re
import secrets
import time
from collections import defaultdict, deque

import uuid

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import and_, func, select

from app.api.v1.portal_acceso import _emitir_sesion, _firmar, _leer, marcar_equipo
from app.api.v1.portal_auth import PortalUser
from app.config import get_settings
from app.deps import DBSession
from app.models.crm import Customer

log = logging.getLogger("portal.codigo")
router = APIRouter(prefix="/portal/auth", tags=["portal"])

CODIGO_MIN = 10
REVISORES = {d.strip() for d in os.getenv("PORTAL_REVISOR_DOCS", "1000000001").split(",") if d.strip()}
_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)


# ── topes ──────────────────────────────────────────────────────────────
_por_ip: dict[str, deque] = defaultdict(deque)


def ip_de(request: Request) -> str:
    h = request.headers
    return (h.get("cf-connecting-ip") or (h.get("x-forwarded-for") or "").split(",")[0].strip()
            or (request.client.host if request.client else "?"))


def frenar_ip(request: Request, tope: int = 40, ventana: int = 900) -> None:
    """Freno por IP (por proceso). Generoso: detrás del proxy muchas IP llegan iguales."""
    q, ahora = _por_ip[ip_de(request)], time.time()
    while q and q[0] < ahora - ventana:
        q.popleft()
    if len(q) >= tope:
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera unos minutos.")
    q.append(ahora)


def _ahora() -> int:
    return int(time.time())


def bloqueo_cedula(c: Customer) -> None:
    f = (c.extra or {}).get("acceso_fallos") or {}
    if f.get("n", 0) >= 5 and _ahora() - f.get("desde", 0) < 900:
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos con esta cédula. Espera 15 minutos o entra con Google.",
        )


def sumar_fallo(c: Customer) -> None:
    extra = copy.deepcopy(c.extra or {})
    f = extra.get("acceso_fallos") or {}
    if _ahora() - f.get("desde", 0) >= 900:
        f = {"n": 0, "desde": _ahora()}
    f["n"] = f.get("n", 0) + 1
    extra["acceso_fallos"] = f
    c.extra = extra


def telefono_no_coincide(c: Customer) -> str:
    """Mensaje claro (8-nov-2026: Diego escribió el teléfono de la tienda y no entendió el error)."""
    fin = re.sub(r"\D", "", c.phone or "")[-2:]
    pista = f" (el registrado termina en {fin})" if fin else ""
    return (f"Ese teléfono no es el que tenemos con esta cédula{pista}. "
            "Usa el celular que diste en la tienda o escríbenos por WhatsApp al 320 687 6633.")


def _limpiar_fallos(c: Customer) -> None:
    extra = copy.deepcopy(c.extra or {})
    if extra.pop("acceso_fallos", None) is not None:
        c.extra = extra


# ── celular de confianza ───────────────────────────────────────────────
def equipo_confiable(c: Customer, cookie: str | None) -> bool:
    if not cookie:
        return False
    try:
        d = _leer(cookie)
    except HTTPException:
        return False
    return d.get("t") == "eq" and d.get("u") == str(c.id)


# ── el código ──────────────────────────────────────────────────────────
def _huella(cid, codigo: str) -> str:
    return hmac.new(get_settings().jwt_secret.encode(), f"{cid}:{codigo}".encode(), hashlib.sha256).hexdigest()


def ocultar(correo: str) -> str:
    usuario, _, dominio = correo.partition("@")
    return f"{usuario[:2]}{'•' * max(2, len(usuario) - 2)}@{dominio}"


def _mandar(c: Customer, correo: str, pendiente: bool) -> None:
    """Genera, guarda (solo su huella) y envía un código. `pendiente`: el correo aún no es del cliente."""
    extra = copy.deepcopy(c.extra or {})
    envios = [t for t in extra.get("acceso_envios", []) if _ahora() - t < 3600]
    if len(envios) >= 5:
        raise HTTPException(status_code=429, detail="Ya te mandamos 5 códigos en la última hora. Espera un rato o entra con Google.")
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    extra["acceso_codigo"] = {"h": _huella(c.id, codigo), "exp": _ahora() + CODIGO_MIN * 60, "i": 0,
                              "correo": correo if pendiente else None}
    extra["acceso_envios"] = envios + [_ahora()]
    c.extra = extra

    from app.services.email import send_email

    nombre = html.escape((c.full_name or "").split(" ")[0] or "Hola")
    cuerpo = f"""
    <div style="font-family:Arial,sans-serif;max-width:420px;margin:auto;padding:24px;color:#1f2937">
      <p style="font-size:16px">{nombre}, este es tu código para entrar a Bigotes y Paticas:</p>
      <p style="font-size:36px;font-weight:bold;letter-spacing:8px;text-align:center;margin:24px 0;color:#187f77">{codigo}</p>
      <p style="font-size:14px">Vence en {CODIGO_MIN} minutos. Si no fuiste tú, ignora este correo: nadie puede entrar sin este código.</p>
      <p style="font-size:12px;color:#6b7280">Nunca te lo pediremos por teléfono ni por WhatsApp.</p>
    </div>"""
    ok = send_email(correo, f"{codigo} es tu código de Bigotes y Paticas", cuerpo,
                    text=f"Tu código para entrar a Bigotes y Paticas es {codigo}. Vence en {CODIGO_MIN} minutos.")
    log.info("codigo enviado cliente=%s correo=%s ok=%s pendiente=%s", c.id, ocultar(correo), ok, pendiente)
    if not ok:
        raise HTTPException(status_code=502, detail="No pudimos enviar el correo. Intenta de nuevo o entra con Google.")


def respuesta_codigo(c: Customer, correo: str, extra_reto: dict | None = None) -> dict:
    return {"status": "code_required", "email_hint": ocultar(correo),
            "reto": _firmar({"t": "otp", "u": str(c.id), **(extra_reto or {})}, ttl=1800)}


async def paso_seguro(db, request: Request, response: Response, c: Customer,
                      equipo: str | None, extra_reto: dict | None = None) -> dict:
    """Cédula + teléfono ya coinciden: ¿se abre la sesión o se pide código?"""
    _limpiar_fallos(c)
    if c.document_id in REVISORES or equipo_confiable(c, equipo):
        return await _emitir_sesion(db, response, c)
    if c.email and _CORREO.match(c.email):
        _mandar(c, c.email, pendiente=False)
        await db.commit()
        return respuesta_codigo(c, c.email, extra_reto)
    await db.commit()
    return {"status": "email_required",
            "reto": _firmar({"t": "pide_correo", "u": str(c.id), **(extra_reto or {})}, ttl=1800)}


async def _cliente(db, cid: str) -> Customer:
    try:
        cid_uuid = uuid.UUID(cid)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Solicitud inválida")
    c = (await db.execute(select(Customer).where(Customer.id == cid_uuid))).scalar_one_or_none()
    if not c or c.deleted_at is not None or (c.extra or {}).get("eliminacion"):
        raise HTTPException(status_code=401, detail="No encontramos tu cuenta")
    return c


async def _correo_libre(db, correo: str, c: Customer) -> None:
    otro = (await db.execute(select(Customer.id).where(and_(
        func.lower(Customer.email) == correo, Customer.id != c.id, Customer.deleted_at == None,  # noqa: E711
    )))).first()
    if otro:
        raise HTTPException(status_code=409, detail="Ese correo ya está en otra cuenta. Usa otro o escríbenos por WhatsApp al 320 687 6633.")


def _validar_correo(correo: str) -> str:
    correo = (correo or "").strip().lower()
    if not _CORREO.match(correo) or len(correo) > 120:
        raise HTTPException(status_code=422, detail="Escribe un correo válido")
    return correo


def _comprobar(c: Customer, codigo: str) -> dict:
    extra = copy.deepcopy(c.extra or {})
    reg = extra.get("acceso_codigo")
    if not reg or reg.get("exp", 0) < _ahora():
        raise HTTPException(status_code=400, detail="El código venció. Pide uno nuevo.")
    if reg.get("i", 0) >= 5:
        raise HTTPException(status_code=429, detail="Demasiados intentos. Pide un código nuevo.")
    if not hmac.compare_digest(reg["h"], _huella(c.id, re.sub(r"\D", "", codigo or ""))):
        reg["i"] = reg.get("i", 0) + 1
        extra["acceso_codigo"] = reg
        c.extra = extra
        raise HTTPException(status_code=401, detail="Código incorrecto")
    extra.pop("acceso_codigo", None)
    c.extra = extra
    return reg


def _guardar_correo(c: Customer, correo: str) -> None:
    c.email = correo
    extra = copy.deepcopy(c.extra or {})
    extra["correo_verificado"] = correo
    c.extra = extra
    log.info("correo verificado cliente=%s correo=%s", c.id, ocultar(correo))


# ── al entrar ──────────────────────────────────────────────────────────
class CorreoIn(BaseModel):
    reto: str
    email: str


class RetoIn(BaseModel):
    reto: str


class VerificarIn(BaseModel):
    reto: str
    codigo: str


@router.post("/login/correo")
async def login_correo(payload: CorreoIn, request: Request, db: DBSession) -> dict:
    """Cliente sin correo: registra uno y se le manda ahí el código."""
    frenar_ip(request)
    st = _leer(payload.reto)
    if st.get("t") != "pide_correo":
        raise HTTPException(status_code=400, detail="Solicitud inválida")
    c = await _cliente(db, st["u"])
    if c.email and _CORREO.match(c.email):
        raise HTTPException(status_code=409, detail="Tu cuenta ya tiene correo. Vuelve a ingresar.")
    correo = _validar_correo(payload.email)
    await _correo_libre(db, correo, c)
    _mandar(c, correo, pendiente=True)
    await db.commit()
    return respuesta_codigo(c, correo, {k: v for k, v in st.items() if k == "gsub"})


@router.post("/login/reenviar")
async def login_reenviar(payload: RetoIn, request: Request, db: DBSession) -> dict:
    frenar_ip(request)
    st = _leer(payload.reto)
    if st.get("t") != "otp":
        raise HTTPException(status_code=400, detail="Solicitud inválida")
    c = await _cliente(db, st["u"])
    reg = (c.extra or {}).get("acceso_codigo") or {}
    correo = reg.get("correo") or c.email
    if not correo:
        raise HTTPException(status_code=400, detail="Vuelve a ingresar")
    _mandar(c, correo, pendiente=bool(reg.get("correo")))
    await db.commit()
    return {"ok": True, "email_hint": ocultar(correo)}


@router.post("/login/verificar")
async def login_verificar(payload: VerificarIn, request: Request, response: Response, db: DBSession) -> dict:
    frenar_ip(request)
    st = _leer(payload.reto)
    if st.get("t") != "otp":
        raise HTTPException(status_code=400, detail="Solicitud inválida")
    c = await _cliente(db, st["u"])
    try:
        reg = _comprobar(c, payload.codigo)
    finally:
        await db.commit()
    if reg.get("correo"):
        await _correo_libre(db, reg["correo"], c)
        _guardar_correo(c, reg["correo"])
    elif c.email:
        extra = copy.deepcopy(c.extra or {}); extra["correo_verificado"] = c.email.lower(); c.extra = extra
    if st.get("gsub"):
        extra = copy.deepcopy(c.extra or {}); extra["google_sub"] = st["gsub"]; c.extra = extra
    return await _emitir_sesion(db, response, c)


# ── con la sesión abierta: agregar el correo ───────────────────────────
class MiCorreoIn(BaseModel):
    email: str


class MiCodigoIn(BaseModel):
    codigo: str


@router.post("/me/correo")
async def mi_correo(payload: MiCorreoIn, request: Request, db: DBSession, customer: Customer = PortalUser) -> dict:
    frenar_ip(request)
    correo = _validar_correo(payload.email)
    await _correo_libre(db, correo, customer)
    _mandar(customer, correo, pendiente=True)
    await db.commit()
    return {"ok": True, "email_hint": ocultar(correo)}


@router.post("/me/correo/verificar")
async def mi_correo_verificar(payload: MiCodigoIn, request: Request, response: Response,
                              db: DBSession, customer: Customer = PortalUser) -> dict:
    frenar_ip(request)
    try:
        reg = _comprobar(customer, payload.codigo)
    finally:
        await db.commit()
    correo = reg.get("correo") or customer.email
    if not correo:
        raise HTTPException(status_code=400, detail="Pide el código otra vez")
    await _correo_libre(db, correo, customer)
    _guardar_correo(customer, correo)
    marcar_equipo(response, customer)
    await db.commit()
    return {"ok": True, "email": correo}


@router.get("/me/seguridad")
async def mi_seguridad(customer: Customer = PortalUser) -> dict:
    extra = customer.extra or {}
    return {
        "email": customer.email,
        "correo_verificado": bool(customer.email) and extra.get("correo_verificado") == (customer.email or "").lower(),
        "google": bool(extra.get("google_sub")),
        "huellas": len(extra.get("passkeys", [])),
    }
