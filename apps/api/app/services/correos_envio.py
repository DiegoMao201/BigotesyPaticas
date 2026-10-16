"""Correos al cliente de un envío nacional (16-oct-2026).

Diego: *"como es una compra en línea, pedirle al cliente la información importante
para la comunicación efectiva en caso de algún retraso o inconvenientes [...] la
idea es crecer el negocio hacia las ventas, no ganarme problemas por mala
comunicación"*.

Dos correos, y ninguno promete lo que no se puede cumplir:

1. **Compra confirmada** (al confirmarse el pago): qué compró, a dónde va, con
   quién, cuánto tarda, cómo contactarnos. Dice claro que la guía llega DESPUÉS,
   cuando el pedido se aliste; no lo deja esperando frente a una pantalla.
2. **Guía lista** (al generarse): número, transportadora, enlace de rastreo y el
   reparto de responsabilidades: la compra es con Bigotes y Paticas, el
   transporte lo hace la transportadora.

Nunca lanzan. Un correo que no sale se registra y la venta sigue.
"""

from __future__ import annotations

import asyncio
import logging

from app.models.portal import PortalOrder, Shipment
from app.services.email import STORE_EMAIL, send_email

log = logging.getLogger(__name__)

TIENDA = "Bigotes y Paticas"
TEL = "320 687 6633"
WA = "https://wa.me/573206876633"
DIRECCION = "Samara Plaza Mall, Cl. 15 #3A-07 Local 2, Dosquebradas, Risaralda"
HORARIO = "lunes a sábado, 10:00 a. m. a 7:00 p. m."

#: Quién responde por qué. Es el mismo texto que ve en el checkout y en los
#: términos: no se le dice una cosa al pagar y otra al reclamar.
RESPONSABILIDADES = (
    "<p style='font-size:13px;color:#555;line-height:1.5'><b>Quién responde por qué.</b> "
    f"Tu compra es con <b>{TIENDA}</b>: respondemos por el producto, su estado y su empaque, "
    "y somos tu contacto para cualquier duda. El transporte lo realiza la <b>transportadora que "
    "elegiste</b>, contratada a través de Envia.com: ella define los tiempos de entrega y "
    "responde por el paquete mientras está en su poder. Si hay un retraso, un daño o una "
    "pérdida en el camino, escríbenos de inmediato: la reclamación se presenta ante la "
    "transportadora y nosotros la gestionamos contigo hasta resolverla.</p>"
)


def _pesos(v: float | int | None) -> str:
    return f"${int(v or 0):,}".replace(",", ".")


def _pie() -> str:
    return (
        f"<hr style='border:none;border-top:1px solid #e5e5e5;margin:20px 0'>"
        f"<p style='font-size:13px;color:#555'><b>{TIENDA}</b><br>{DIRECCION}<br>"
        f"WhatsApp y teléfono: <a href='{WA}'>{TEL}</a> · {HORARIO}<br>"
        f"Representante legal: Diego Mauricio García</p>"
    )


def _destinatario(pedido: PortalOrder) -> str | None:
    d = pedido.shipping_destination or {}
    correo = (d.get("email") or "").strip()
    return correo if "@" in correo else None


async def _enviar(to: str, asunto: str, html: str, ref: str) -> None:
    try:
        ok = await asyncio.wait_for(
            asyncio.to_thread(send_email, to, asunto, html, cc=[STORE_EMAIL]), timeout=25
        )
        log.info("CORREO · %s a %s para %s: %s", asunto, to, ref, "enviado" if ok else "NO salió")
    except Exception:
        log.exception("CORREO · falló %s para %s", asunto, ref)


async def compra_confirmada(pedido: PortalOrder, items: list[dict]) -> None:
    """`items`: [{"nombre", "cantidad", "subtotal"}]."""
    to = _destinatario(pedido)
    if not to or pedido.shipping_mode != "national":
        return
    d = pedido.shipping_destination or {}
    q = pedido.shipping_quote or {}
    filas = "".join(
        f"<tr><td style='padding:4px 0'>{i['nombre']} x {i['cantidad']}</td>"
        f"<td style='text-align:right;padding:4px 0'>{_pesos(i['subtotal'])}</td></tr>"
        for i in items
    )
    subtotal = sum(float(i["subtotal"] or 0) for i in items)
    html = (
        f"<div style='font-family:Arial,sans-serif;max-width:560px;color:#222'>"
        f"<h2 style='color:#187f77'>¡Compra confirmada! 🐾</h2>"
        f"<p>Hola {(d.get('nombre') or '').split(' ')[0] or 'de nuevo'}, recibimos tu pago y tu pedido "
        f"<b>{pedido.order_reference}</b> ya está en nuestras manos.</p>"
        f"<table style='width:100%;border-collapse:collapse;font-size:14px'>{filas}"
        f"<tr><td style='padding-top:8px;border-top:1px solid #e5e5e5'>Productos</td>"
        f"<td style='text-align:right;padding-top:8px;border-top:1px solid #e5e5e5'>{_pesos(subtotal)}</td></tr>"
        f"<tr><td>Envío por {q.get('carrier_nombre') or 'transportadora'}</td>"
        f"<td style='text-align:right'>{_pesos(q.get('precio'))}</td></tr>"
        f"<tr><td style='padding-top:6px'><b>Total pagado</b></td>"
        f"<td style='text-align:right;padding-top:6px'><b>{_pesos(pedido.bold_amount or pedido.total_amount)}</b></td></tr>"
        f"</table>"
        f"<h3 style='color:#0d4a45;margin-top:22px'>Dónde lo entregamos</h3>"
        f"<p style='font-size:14px'>{d.get('recibe') or d.get('nombre') or ''}<br>"
        f"{d.get('calle') or ''}{(', ' + d['barrio']) if d.get('barrio') else ''}<br>"
        f"{d.get('ciudad') or ''}, {d.get('departamento_nombre') or ''}"
        f"{('<br>' + d['referencia']) if d.get('referencia') else ''}<br>"
        f"Celular de contacto: {d.get('telefono') or ''}</p>"
        f"<h3 style='color:#0d4a45'>Qué sigue</h3>"
        f"<ol style='font-size:14px;line-height:1.6'>"
        f"<li>Alistamos y empacamos tu pedido en la tienda.</li>"
        f"<li>Generamos la guía con <b>{q.get('carrier_nombre') or 'la transportadora'}</b> y te la "
        f"enviamos por WhatsApp y a este correo, con el enlace para rastrear el paquete.</li>"
        f"<li>La transportadora lo entrega en <b>{q.get('dias') or 'pocos días'}</b> desde que lo recoge. "
        f"No tienes que pagar nada al recibirlo.</li></ol>"
        f"<p style='font-size:14px'>Si algo cambia o tienes una duda, escríbenos a "
        f"<a href='{WA}'>WhatsApp {TEL}</a> con la referencia <b>{pedido.order_reference}</b>.</p>"
        f"{RESPONSABILIDADES}{_pie()}</div>"
    )
    await _enviar(to, f"Compra confirmada · {pedido.order_reference} · {TIENDA}", html, pedido.order_reference or "")


async def guia_lista(pedido: PortalOrder, guia: Shipment) -> None:
    to = _destinatario(pedido)
    if not to:
        return
    d = pedido.shipping_destination or {}
    q = pedido.shipping_quote or {}
    carrier = q.get("carrier_nombre") or guia.carrier
    rastreo = (
        f"<p><a href='{guia.track_url}' style='display:inline-block;background:#187f77;color:#fff;"
        f"padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:bold'>Rastrear mi paquete</a></p>"
        if guia.track_url else ""
    )
    html = (
        f"<div style='font-family:Arial,sans-serif;max-width:560px;color:#222'>"
        f"<h2 style='color:#187f77'>Tu pedido ya tiene guía 📦</h2>"
        f"<p>Hola {(d.get('nombre') or '').split(' ')[0] or ''}, tu pedido <b>{pedido.order_reference}</b> "
        f"sale con <b>{carrier}</b>.</p>"
        f"<p style='font-size:18px'>Guía: <b style='font-family:monospace'>{guia.tracking_number}</b></p>"
        f"{rastreo}"
        f"<p style='font-size:14px'>Tiempo estimado: <b>{q.get('dias') or 'pocos días'}</b> desde que la "
        f"transportadora recibe el paquete. Va para {d.get('calle') or ''}, {d.get('ciudad') or ''}. "
        f"Ya está pagado: no pagas nada al recibir.</p>"
        f"<p style='font-size:14px'>Si la transportadora no te encuentra, suele intentar de nuevo o dejarlo en "
        f"su oficina más cercana; el rastreo te lo dirá. Ante cualquier novedad escríbenos a "
        f"<a href='{WA}'>WhatsApp {TEL}</a>.</p>"
        f"{RESPONSABILIDADES}{_pie()}</div>"
    )
    await _enviar(to, f"Guía {guia.tracking_number} · {carrier} · {TIENDA}", html, pedido.order_reference or "")
