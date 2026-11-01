"""Correo de agradecimiento y calificación después de la compra (1-nov-2026).

Diego: *"quien nos pague con el link de pago o compre directo le enviamos un
correo con la satisfacción de la compra, agradecimiento, algo bien bonito, que
nos califique en Google y que nos califique los productos"*.

Sale cuando el pedido se marca ENTREGADO (ahí el cliente ya tiene el producto en
la mano; antes no hay nada que calificar). Una sola vez por pedido
(`satisfaction_email_sent_at`). Nunca tumba la entrega: todo error se registra y
se sigue.

Calificar un producto es UN clic sobre una estrella del correo, sin iniciar
sesión: el enlace lleva un token firmado con el pedido (`token()`), y el endpoint
público `/v1/public/calificar/...` (reviews.py) registra la reseña como compra
verificada. La calificación en Google va al enlace corto de reseñas de la ficha,
el mismo que ya usa el portal.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from datetime import UTC, datetime
from html import escape

from sqlalchemy import select

from app.config import get_settings
from app.models.catalog import Product
from app.models.crm import Customer
from app.models.portal import Pet, PortalOrder, PortalOrderItem
from app.models.sales import Order as VentaMostrador
from app.models.sales import OrderItem as LineaVenta
from app.services.email import send_email

log = logging.getLogger("correo_satisfaccion")

API_PUBLICA = "https://api.bigotesypaticas.com"
TIENDA = "https://bigotesypaticas.com"
CDN = "https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/branding"
#: Logo recortado en círculo con anillo blanco (generado el 1-nov-2026): el PNG
#: cuadrado dentro de un círculo se veía mal.
LOGO = f"{CDN}/logo-circulo.png"
#: Cinco tiras GIF sincronizadas (4 s en bucle): las estrellas se van llenando una a
#: una y la quinta late con "¡clic!". Los correos no admiten animación CSS; un GIF sí.
#: v2 (1-nov-2026, aprobado por Diego): el doble de resolución, degradado dorado,
#: destello y halo que alumbra; nombre nuevo para saltarse la caché del CDN.
ESTRELLA = f"{CDN}/estrella-{{n}}-v2.gif"
#: Enlace corto de reseñas de la ficha de Google (el mismo del portal de clientes).
RESENA_GOOGLE = "https://g.page/r/CfL67OgLB-10EBM/review"


def token(order_id) -> str:
    """Firma del pedido para calificar sin iniciar sesión. Solo quien recibió el
    correo la tiene; no se puede adivinar ni reutilizar para otro pedido."""
    secreto = get_settings().jwt_secret.encode()
    return hmac.new(secreto, f"calificar:{order_id}".encode(), hashlib.sha256).hexdigest()[:32]


def token_valido(order_id, t: str | None) -> bool:
    return bool(t) and hmac.compare_digest(token(order_id), t or "")


def _estrellas(order_id, product_id) -> str:
    t = token(order_id)
    celdas = []
    for n in range(1, 6):
        url = f"{API_PUBLICA}/v1/public/calificar/{order_id}/{product_id}/{n}?t={t}"
        celdas.append(
            f'<td style="padding:0;"><a href="{url}" title="Calificar con {n} de 5" '
            'style="display:block;text-decoration:none;">'
            f'<img src="{ESTRELLA.format(n=n)}" alt="{"★" * n}" width="64" height="78" '
            'style="display:block;width:64px;height:78px;border:0;"></a></td>'
        )
    return "".join(celdas)


def armar_html(
    nombre: str, mascota: str | None, items: list[dict], order_id, modo: str = "domicilio"
) -> str:
    mostrador = modo == "mostrador"
    saludo = f"¡Gracias, {escape(nombre)}!" if nombre else "¡Gracias por tu compra!"
    quien = (
        f"Esperamos que <strong>{escape(mascota)}</strong> ya esté disfrutando su pedido."
        if mascota
        else "Esperamos que tu peludo ya esté disfrutando su pedido."
    )
    filas = []
    for it in items:
        img = (
            f'<img src="{escape(it["imagen"])}" alt="" width="72" height="72" '
            'style="display:block;width:72px;height:72px;object-fit:contain;border-radius:12px;background:#fff;">'
            if it.get("imagen")
            else '<div style="width:72px;height:72px;border-radius:12px;background:#fff;text-align:center;line-height:72px;font-size:30px;">🐾</div>'
        )
        estrellas = _estrellas(order_id, it["product_id"]) if it.get("product_id") else ""
        filas.append(
            f"""
        <tr><td style="padding:0 0 12px;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f7f6;border-radius:16px;">
            <tr>
              <td style="padding:14px;width:72px;vertical-align:middle;">{img}</td>
              <td style="padding:14px 14px 14px 4px;vertical-align:middle;">
                <p style="margin:0 0 4px;color:#1a1a1a;font-size:15px;font-weight:700;line-height:1.3;">{escape(it["nombre"])}</p>
                <p style="margin:0 0 8px;color:#6b7280;font-size:12px;">Cantidad: {it["cantidad"]}</p>
                {f'<p style="margin:0 0 6px;color:#187f77;font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;">¿Qué tal te pareció? Toca una estrella</p><table cellpadding="0" cellspacing="0"><tr>{estrellas}</tr></table><p style="margin:2px 0 0;color:#9ca3af;font-size:11px;">5 estrellas si te encantó · 1 si no te gustó</p>' if estrellas else ""}
              </td>
            </tr>
          </table>
        </td></tr>"""
        )
    productos = "".join(filas)
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gracias por tu compra</title></head>
<body style="margin:0;padding:0;background:#f0f7f6;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f7f6;padding:32px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

      <tr><td style="background:#187f77;border-radius:20px 20px 0 0;padding:36px 40px 28px;text-align:center;">
        <img src="{LOGO}" alt="Bigotes y Paticas" width="104" height="104" style="display:block;margin:0 auto 14px;width:104px;height:104px;border:0;">
        <p style="color:#a8ddd9;font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;margin:0 0 8px;">BIGOTES Y PATICAS · DOSQUEBRADAS</p>
        <h1 style="color:#ffffff;font-size:28px;font-weight:800;margin:0;line-height:1.2;">{saludo} 🐾</h1>
        <p style="color:#a8ddd9;font-size:16px;margin:10px 0 0;">{"Gracias por visitarnos" if mostrador else "Tu pedido ya llegó a casa"}</p>
      </td></tr>

      <tr><td style="background:#ffffff;padding:32px 40px 8px;">
        <p style="color:#1a1a1a;font-size:16px;line-height:1.6;margin:0 0 24px;">
          {quien} Comprar en una tienda del barrio es confiar, y nosotros lo sabemos:
          por eso cada pedido lo preparamos como si fuera para los nuestros.
        </p>

        <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 20px;">
          <tr><td style="background:linear-gradient(135deg,#fff7f4 0%,#ffe8df 100%);border:2px dashed #FF6B35;border-radius:16px;padding:26px;text-align:center;">
            <p style="color:#FF6B35;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;margin:0 0 8px;">⭐ ¿NOS REGALAS UN MINUTO?</p>
            <p style="color:#1a1a1a;font-size:15px;line-height:1.5;margin:0 0 16px;">
              Tu opinión en Google es lo que hace que otra familia de Pereira y Dosquebradas nos encuentre.
            </p>
            <a href="{RESENA_GOOGLE}" style="display:inline-block;background:#FF6B35;color:#ffffff;font-size:16px;font-weight:800;text-decoration:none;padding:14px 30px;border-radius:12px;">Calificarnos en Google</a>
          </td></tr>
        </table>

        <p style="color:#187f77;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;margin:0 0 12px;">{"Lo que llevaste" if mostrador else "Lo que recibiste"}</p>
        <table width="100%" cellpadding="0" cellspacing="0">{productos}</table>
        <p style="color:#6b7280;font-size:12px;line-height:1.5;margin:4px 0 20px;">
          Un solo clic, sin contraseñas. Las calificaciones de 5 estrellas suman puntos en tu portal de cliente.
        </p>
      </td></tr>

      <tr><td style="background:#ffffff;border-radius:0 0 20px 20px;padding:8px 40px 32px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f7f6;border-radius:14px;">
          <tr><td style="padding:18px 22px;">
            <p style="margin:0 0 6px;color:#1a1a1a;font-size:14px;font-weight:700;">¿Algo no salió como esperabas?</p>
            <p style="margin:0;color:#4b5563;font-size:13px;line-height:1.5;">Responde este correo y lo resolvemos. Preferimos saberlo por ti que por nadie más.</p>
          </td></tr>
        </table>
        <p style="color:#9ca3af;font-size:11px;text-align:center;margin:24px 0 0;line-height:1.6;">
          Bigotes y Paticas · Dosquebradas, Risaralda · <a href="{TIENDA}" style="color:#187f77;text-decoration:none;">bigotesypaticas.com</a>
        </p>
      </td></tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


async def _items(db, order: PortalOrder) -> list[dict]:
    filas = (
        (
            await db.execute(
                select(PortalOrderItem)
                .where(PortalOrderItem.portal_order_id == order.id)
                .where(PortalOrderItem.is_removed.is_(False))
                .order_by(PortalOrderItem.created_at)
            )
        )
        .scalars()
        .all()
    )
    if not filas and order.product_name:
        imagen = None
        if order.product_id:
            imagen = (
                await db.execute(
                    select(Product.primary_image_url).where(Product.id == order.product_id)
                )
            ).scalar_one_or_none()
        return [
            {
                "nombre": order.product_name,
                "cantidad": int(order.quantity or 1),
                "imagen": imagen,
                "product_id": order.product_id,
            }
        ]
    out = []
    for f in filas:
        imagen = f.image_url
        if not imagen and f.product_id:
            imagen = (
                await db.execute(
                    select(Product.primary_image_url).where(Product.id == f.product_id)
                )
            ).scalar_one_or_none()
        out.append(
            {
                "nombre": f.name or "Producto",
                "cantidad": int(f.quantity or 1),
                "imagen": imagen,
                "product_id": f.product_id,
            }
        )
    return out


async def enviar(db, order: PortalOrder) -> bool:
    """Manda el correo de agradecimiento. Idempotente. No lanza excepciones."""
    try:
        if order.satisfaction_email_sent_at is not None:
            return False
        cliente = (
            await db.execute(select(Customer).where(Customer.id == order.customer_id))
        ).scalar_one_or_none()
        correo = (cliente.email if cliente else None) or order.bold_payer_email
        if not correo:
            log.info("satisfaccion: pedido %s sin correo de cliente; no se manda", order.id)
            return False
        nombre = ((cliente.full_name if cliente else "") or "").strip().split(" ")[0]
        mascota = None
        if order.pet_id:
            mascota = (
                await db.execute(select(Pet.name).where(Pet.id == order.pet_id))
            ).scalar_one_or_none()
        items = await _items(db, order)
        html = armar_html(nombre, mascota, items, order.id)
        asunto = (
            f"{nombre}, gracias por tu compra 🐾 ¿nos calificas?"
            if nombre
            else "Gracias por tu compra 🐾 ¿nos calificas?"
        )
        ok = await asyncio.to_thread(send_email, correo, asunto, html)
        if ok:
            order.satisfaction_email_sent_at = datetime.now(UTC)
            log.info("satisfaccion: correo enviado a %s por el pedido %s", correo, order.id)
        else:
            log.warning("satisfaccion: el envío a %s falló (pedido %s)", correo, order.id)
        return bool(ok)
    except Exception:  # nunca tumba la entrega
        log.exception("satisfaccion: error mandando el correo del pedido %s", order.id)
        return False


async def enviar_venta(db, venta: VentaMostrador) -> bool:
    """El mismo correo para una venta de mostrador (POS) con cliente que tenga
    correo. El candado vive en `metadata.correo_gracias_at`: una sola vez por venta.
    No lanza excepciones."""
    try:
        meta = dict(venta.metadata_ or {})
        if meta.get("correo_gracias_at") or not venta.customer_id:
            return False
        cliente = (
            await db.execute(select(Customer).where(Customer.id == venta.customer_id))
        ).scalar_one_or_none()
        correo = (cliente.email or "").strip() if cliente else ""
        if not correo:
            return False
        nombre = ((cliente.full_name if cliente else "") or "").strip().split(" ")[0]
        mascota = ((cliente.extra or {}).get("pet_name") if cliente else None) or None
        lineas = (
            await db.execute(
                select(LineaVenta, Product.primary_image_url)
                .outerjoin(Product, Product.id == LineaVenta.product_id)
                .where(LineaVenta.order_id == venta.id)
            )
        ).all()
        items = [
            {
                "nombre": li.name_snapshot or "Producto",
                "cantidad": int(li.quantity or 1),
                "imagen": imagen,
                "product_id": li.product_id,
            }
            for li, imagen in lineas
        ]
        if not items:
            return False
        html = armar_html(nombre, mascota, items, venta.id, modo="mostrador")
        asunto = (
            f"{nombre}, gracias por tu compra 🐾 ¿nos calificas?"
            if nombre
            else "Gracias por tu compra 🐾 ¿nos calificas?"
        )
        ok = await asyncio.to_thread(send_email, correo, asunto, html)
        if ok:
            meta["correo_gracias_at"] = datetime.now(UTC).isoformat()
            venta.metadata_ = meta
            log.info(
                "satisfaccion: correo enviado a %s por la venta %s", correo, venta.order_number
            )
        return bool(ok)
    except Exception:  # nunca tumba la venta
        log.exception("satisfaccion: error mandando el correo de la venta %s", venta.id)
        return False
