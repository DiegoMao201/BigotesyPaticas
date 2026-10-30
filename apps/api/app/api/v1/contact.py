"""Contact form and newsletter subscription."""

from __future__ import annotations

import html
import logging
import re
import time
from collections import deque

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.bono_bienvenida import CODIGO as WELCOME_COUPON
from app.services.email import STORE_EMAIL, send_email

router = APIRouter(prefix="/contact", tags=["contact"])
log = logging.getLogger(__name__)

# 24-oct-2026: llegaron "Contacto web: YlyNrZbIWKnIoGSrIcuTNmrM" con correos de terceros
# (tony.r@pacemetals.com…). Son bots de spam: llenan formularios con texto al azar y el
# correo de una víctima, y el formulario le mandaba a esa víctima nuestro autorresponder
# desde hola@bigotesypaticas.com (daña la reputación del dominio: los correos de pedidos y
# pagos empiezan a caer en spam). Además el nombre y el mensaje iban al HTML sin escapar.
# Defensa: campo trampa invisible, filtro de texto al azar, tope por IP y tope global.
MAX_POR_IP_HORA = 20      # la API ve a todos detrás del proxy (10.0.1.1): esto es casi un tope global
MAX_GLOBAL_HORA = 40
_por_ip: dict[str, deque] = {}
_global: deque = deque()
_AZAR = re.compile(r"^[A-Za-z]{10,}$")


def _ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def _pasa_tope(ip: str) -> bool:
    ahora = time.monotonic()
    for q in (_por_ip.setdefault(ip, deque()), _global):
        while q and ahora - q[0] > 3600:
            q.popleft()
    if len(_por_ip[ip]) >= MAX_POR_IP_HORA or len(_global) >= MAX_GLOBAL_HORA:
        return False
    _por_ip[ip].append(ahora); _global.append(ahora)
    if len(_por_ip) > 5000:
        for k in list(_por_ip)[:1000]:
            _por_ip.pop(k, None)
    return True


def es_texto_al_azar(t: str) -> bool:
    """Una sola 'palabra' de 10+ letras con mayúsculas metidas en medio: YlyNrZbIWKnIoGSrIcuTNmrM.
    Un nombre o mensaje real tiene espacios o no alterna mayúsculas así."""
    t = (t or "").strip()
    return bool(_AZAR.match(t)) and sum(c.isupper() for c in t[1:]) >= 3


class ContactForm(BaseModel):
    name: str = Field(max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    message: str = Field(max_length=4000)
    website: str | None = None   # campo trampa: invisible para personas, los bots lo llenan


class NewsletterIn(BaseModel):
    email: EmailStr
    source: str = Field(default="store_footer", max_length=40)
    website: str | None = None


@router.post("/send")
async def send_contact(payload: ContactForm, bg: BackgroundTasks, request: Request) -> dict:
    """Forward contact form to store email and send auto-reply to sender."""
    ip = _ip(request)
    if payload.website or es_texto_al_azar(payload.name) or es_texto_al_azar(payload.message):
        log.warning("contacto descartado como spam ip=%s email=%s", ip, payload.email)
        return {"ok": True}     # al bot se le dice que sí: si sabe que lo frenamos, cambia
    if not _pasa_tope(ip):
        log.warning("contacto frenado por tope ip=%s", ip)
        return {"ok": True}

    e = lambda t: html.escape(t or "")

    def _send() -> None:
        phone_line = f"<p><strong>Teléfono:</strong> {e(payload.phone)}</p>" if payload.phone else ""
        store_html = f"""
        <h2 style="color:#187f77;">Nuevo mensaje desde bigotesypaticas.com</h2>
        <p><strong>Nombre:</strong> {e(payload.name)}</p>
        <p><strong>Email:</strong> {e(payload.email)}</p>
        {phone_line}
        <hr style="border:none;border-top:1px solid #eee;margin:12px 0;">
        <p style="color:#555;">{e(payload.message).replace(chr(10), '<br>')}</p>
        """
        asunto = re.sub(r"[\r\n]+", " ", payload.name)[:80]
        send_email(STORE_EMAIL, f"Contacto web: {asunto}", store_html)

        first = e(payload.name.split()[0][:40]) if payload.name.strip() else "cliente"
        reply_html = f"""
        <h2 style="color:#187f77;">¡Hola, {first}!</h2>
        <p>Gracias por escribirnos. Recibimos tu mensaje y te responderemos a la brevedad.</p>
        <br>
        <p>Con cariño,<br><strong>El equipo de Bigotes y Paticas</strong></p>
        <p style="color:#888;font-size:12px;">
          📱 +57 320 687 6633 &nbsp;·&nbsp;
          Dosquebradas, Risaralda
        </p>
        """
        send_email(payload.email, "Recibimos tu mensaje — Bigotes y Paticas", reply_html)

    bg.add_task(_send)
    return {"ok": True}


class ReviewIn(BaseModel):
    stars: int
    comment: str | None = None
    source: str | None = "store"


@router.post("/review")
async def submit_review(payload: ReviewIn, bg: BackgroundTasks) -> dict:
    """Capture internal star rating and notify admin."""

    def _send() -> None:
        stars_txt = "⭐" * min(max(payload.stars, 1), 5)
        send_email(
            STORE_EMAIL,
            f"Nueva calificación {stars_txt} — {payload.source}",
            f"""
            <h2 style="color:#187f77;">Nueva calificación interna</h2>
            <p><strong>Estrellas:</strong> {stars_txt} ({payload.stars}/5)</p>
            <p><strong>Fuente:</strong> {payload.source}</p>
            {"<p><strong>Comentario:</strong> " + payload.comment + "</p>" if payload.comment else ""}
            """,
        )

    bg.add_task(_send)
    return {"ok": True}




def _welcome_html(email: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bienvenido</title></head>
<body style="margin:0;padding:0;background:#f0f7f6;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f7f6;padding:32px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

      <!-- HEADER verde -->
      <tr><td style="background:#187f77;border-radius:20px 20px 0 0;padding:36px 40px 28px;text-align:center;">
        <img src="https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/logo-white.png"
             alt="Bigotes y Paticas" width="120" style="display:block;margin:0 auto 16px;max-width:120px;"
             onerror="this.style.display='none'">
        <p style="color:#a8ddd9;font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;margin:0 0 8px;">
          BIGOTES Y PATICAS · DOSQUEBRADAS
        </p>
        <h1 style="color:#ffffff;font-size:28px;font-weight:800;margin:0;line-height:1.2;">
          ¡Bienvenido al Club! 🐾
        </h1>
        <p style="color:#a8ddd9;font-size:16px;margin:10px 0 0;">
          Tu familia de mascotas tiene un nuevo hogar
        </p>
      </td></tr>

      <!-- CUERPO blanco -->
      <tr><td style="background:#ffffff;padding:36px 40px;">

        <!-- Saludo -->
        <p style="color:#1a1a1a;font-size:16px;line-height:1.6;margin:0 0 20px;">
          Gracias por suscribirte a nuestra comunidad. En Bigotes y Paticas encontrarás todo
          lo que tu mascota necesita — alimento premium, accesorios, grooming y atención veterinaria —
          con el calor de un negocio local que los quiere tanto como tú.
        </p>

        <!-- CUPÓN destacado -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin:28px 0;">
          <tr><td style="background:linear-gradient(135deg,#fff7f4 0%,#ffe8df 100%);border:2px dashed #FF6B35;border-radius:16px;padding:28px;text-align:center;">
            <p style="color:#FF6B35;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;margin:0 0 8px;">
              🎁 TU REGALO DE BIENVENIDA
            </p>
            <p style="color:#1a1a1a;font-size:15px;margin:0 0 12px;">
              <strong>$5.000 de descuento</strong> en tu primera compra
            </p>
            <div style="background:#ffffff;border:2px solid #FF6B35;border-radius:10px;display:inline-block;padding:10px 28px;margin:4px 0 12px;">
              <span style="color:#FF6B35;font-size:24px;font-weight:900;letter-spacing:4px;">{WELCOME_COUPON}</span>
            </div>
            <p style="color:#888;font-size:12px;margin:8px 0 0;">
              Compras desde $30.000 · Válido 30 días · Un uso por cliente
            </p>
            <p style="color:#555;font-size:12px;margin:8px 0 0;">
              Para usarlo, dinos el correo con el que te suscribiste ({email})
              al pagar en la tienda o al pedir por WhatsApp.
            </p>
          </td></tr>
        </table>

        <!-- PUNTOS -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin:20px 0;">
          <tr><td style="background:#f0f7f6;border-radius:14px;padding:20px 24px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="vertical-align:middle;width:48px;">
                  <div style="width:44px;height:44px;background:#187f77;border-radius:50%;text-align:center;line-height:44px;font-size:22px;">⭐</div>
                </td>
                <td style="vertical-align:middle;padding-left:16px;">
                  <p style="color:#187f77;font-weight:800;font-size:15px;margin:0 0 3px;">50 Puntos Bigotes te esperan</p>
                  <p style="color:#555;font-size:13px;margin:0;">
                    Regístrate en el portal de clientes y reclama tus puntos. ¡Acumula y canjea por descuentos!
                  </p>
                </td>
              </tr>
            </table>
          </td></tr>
        </table>

        <!-- CTA PORTAL -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin:28px 0 8px;">
          <tr><td align="center">
            <a href="https://mi.bigotesypaticas.com/register"
               style="display:inline-block;background:#187f77;color:#ffffff;font-size:15px;font-weight:700;
                      padding:14px 36px;border-radius:50px;text-decoration:none;letter-spacing:0.3px;">
              Registrarme y reclamar mis puntos →
            </a>
          </td></tr>
          <tr><td align="center" style="padding-top:10px;">
            <a href="https://bigotesypaticas.com"
               style="color:#187f77;font-size:13px;text-decoration:none;">
              Ver catálogo completo
            </a>
          </td></tr>
        </table>

        <!-- Qué encontrarás -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin:28px 0 8px;border-top:1px solid #f0f0f0;padding-top:24px;">
          <tr>
            <td width="25%" style="text-align:center;padding:8px;">
              <p style="font-size:28px;margin:0 0 4px;">🛍️</p>
              <p style="color:#187f77;font-size:11px;font-weight:700;margin:0;">Tienda online</p>
            </td>
            <td width="25%" style="text-align:center;padding:8px;">
              <p style="font-size:28px;margin:0 0 4px;">🛵</p>
              <p style="color:#187f77;font-size:11px;font-weight:700;margin:0;">Domicilio</p>
            </td>
            <td width="25%" style="text-align:center;padding:8px;">
              <p style="font-size:28px;margin:0 0 4px;">🛁</p>
              <p style="color:#187f77;font-size:11px;font-weight:700;margin:0;">Grooming</p>
            </td>
            <td width="25%" style="text-align:center;padding:8px;">
              <p style="font-size:28px;margin:0 0 4px;">🩺</p>
              <p style="color:#187f77;font-size:11px;font-weight:700;margin:0;">Veterinaria</p>
            </td>
          </tr>
        </table>

      </td></tr>

      <!-- FOOTER verde oscuro -->
      <tr><td style="background:#0d4a45;border-radius:0 0 20px 20px;padding:28px 40px;text-align:center;">
        <p style="color:#a8ddd9;font-size:13px;margin:0 0 8px;">
          <strong style="color:#ffffff;">Samara Plaza Mall</strong> · Cl. 15 #3A-07 Local 2, Dosquebradas
        </p>
        <p style="color:#a8ddd9;font-size:13px;margin:0 0 16px;">
          📱 <a href="https://wa.me/573206876633" style="color:#5ecdc7;text-decoration:none;">+57 320 687 6633</a>
          &nbsp;·&nbsp; Lun-Sáb 10 AM-7 PM
        </p>
        <table cellpadding="0" cellspacing="0" style="margin:0 auto 16px;">
          <tr>
            <td style="padding:0 6px;">
              <a href="https://instagram.com/bigotesypaticas" style="color:#5ecdc7;font-size:12px;text-decoration:none;">Instagram</a>
            </td>
            <td style="color:#a8ddd9;font-size:12px;">·</td>
            <td style="padding:0 6px;">
              <a href="https://www.tiktok.com/@bigotesypaticas" style="color:#5ecdc7;font-size:12px;text-decoration:none;">TikTok</a>
            </td>
            <td style="color:#a8ddd9;font-size:12px;">·</td>
            <td style="padding:0 6px;">
              <a href="https://www.facebook.com/BigotesyPaticas" style="color:#5ecdc7;font-size:12px;text-decoration:none;">Facebook</a>
            </td>
            <td style="color:#a8ddd9;font-size:12px;">·</td>
            <td style="padding:0 6px;">
              <a href="https://www.youtube.com/@bigotesypaticas" style="color:#5ecdc7;font-size:12px;text-decoration:none;">YouTube</a>
            </td>
            <td style="color:#a8ddd9;font-size:12px;">·</td>
            <td style="padding:0 6px;">
              <a href="https://bigotesypaticas.com" style="color:#5ecdc7;font-size:12px;text-decoration:none;">bigotesypaticas.com</a>
            </td>
          </tr>
        </table>
        <p style="color:#4a8a85;font-size:11px;margin:0;">
          Recibiste este correo porque te suscribiste en bigotesypaticas.com.<br>
          Tu email: {email}
        </p>
      </td></tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


def ALREADY_SUBSCRIBED_HTML(email: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f7f6;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f7f6;padding:32px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#fff;border-radius:20px;overflow:hidden;">
      <tr><td style="background:#187f77;padding:32px;text-align:center;">
        <h1 style="color:#fff;font-size:24px;margin:0;">¡Ya eres parte del club! 🐾</h1>
      </td></tr>
      <tr><td style="padding:32px 40px;text-align:center;">
        <p style="font-size:28px;margin:0 0 12px;">🎉</p>
        <p style="color:#1a1a1a;font-size:16px;line-height:1.6;margin:0 0 16px;">
          Tu correo <strong>{email}</strong> ya está registrado en nuestra comunidad.
        </p>
        <p style="color:#555;font-size:14px;line-height:1.6;margin:0 0 24px;">
          Si todavía no has usado tu cupón <strong style="color:#FF6B35;">PRIMERAPATA</strong>,
          dinos este correo al pagar en la tienda o al pedir por WhatsApp.<br>
          Vale $5.000 en tu primera compra desde $30.000, durante los 30 días
          siguientes al correo de bienvenida.
        </p>
        <a href="https://mi.bigotesypaticas.com"
           style="display:inline-block;background:#187f77;color:#fff;font-size:14px;font-weight:700;
                  padding:12px 28px;border-radius:50px;text-decoration:none;">
          Ver mi portal de puntos →
        </a>
      </td></tr>
      <tr><td style="background:#0d4a45;padding:20px;text-align:center;">
        <p style="color:#a8ddd9;font-size:12px;margin:0;">
          Bigotes y Paticas · Dosquebradas · bigotesypaticas.com
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""


@router.post("/newsletter")
async def newsletter_subscribe(
    payload: NewsletterIn,
    bg: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Suscribe email con deduplicado — un cupón por dirección, siempre."""
    ip = _ip(request)
    if payload.website or not _pasa_tope(ip):
        log.warning("suscripción descartada ip=%s email=%s", ip, payload.email)
        return {"ok": True, "already_subscribed": False}

    # Verificar si ya está suscrito
    row = await db.execute(
        text("SELECT id, coupon_sent_at FROM crm.newsletter_subscribers WHERE email = :e"),
        {"e": payload.email.lower()},
    )
    existing = row.fetchone()

    if existing:
        # Ya suscrito → correo recordatorio sin nuevo cupón
        def _remind() -> None:
            send_email(
                payload.email,
                "¡Ya eres parte del club Bigotes y Paticas! 🐾",
                ALREADY_SUBSCRIBED_HTML(payload.email),
            )

        bg.add_task(_remind)
        return {"ok": True, "already_subscribed": True}

    # Nuevo suscriptor → guardar y enviar bienvenida con cupón
    await db.execute(
        text("""
            INSERT INTO crm.newsletter_subscribers (email, source, coupon_sent_at)
            VALUES (:e, :s, NOW())
            ON CONFLICT (email) DO NOTHING
        """),
        {"e": payload.email.lower(), "s": payload.source},
    )
    await db.commit()

    def _welcome() -> None:
        send_email(
            STORE_EMAIL,
            f"🐾 Nueva suscripción: {payload.email}",
            f"<p>Nuevo suscriptor: <strong>{payload.email}</strong></p>",
        )
        send_email(
            payload.email,
            "🎁 Tu cupón de bienvenida + 50 Puntos Bigotes — Bigotes y Paticas",
            _welcome_html(payload.email),
        )

    bg.add_task(_welcome)
    return {"ok": True, "already_subscribed": False}
