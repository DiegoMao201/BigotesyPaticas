"""Semáforo de riesgo de un pago con Bold, para no despachar un fraude.

Diego (8-oct-2026): *"hacen pagos por la web y a los 15 días piden reembolsos, o son
tarjetas clonadas… yo como comercio pierdo"*.

**Bold no trae esto.** Su webhook tiene cuatro eventos y ninguno es de contracargo;
su manual de ventas no presenciales dice sin rodeos que *"tu negocio asumirá el
riesgo de fraude"*. Lo único que Bold sí da son los datos del pago —tarjeta
enmascarada, tipo, correo del pagador, medio— y una lista de señales de alerta. Este
módulo toma esas señales y las convierte en un número y un color.

**ESTE MÓDULO NO BLOQUEA NINGÚN PAGO.** El pago ya ocurrió y el dinero ya entró;
negarlo aquí no devolvería nada. Lo que hace es decidir si el pedido se puede
despachar tranquilo o si hay que llamar al cliente antes de entregarle la mercancía
—que es, literalmente, la recomendación de Bold: *"siempre que recibas un pedido que
genere sospechas… es mejor llamar a tu cliente para validar la compra"*.

Por eso **nunca puede tumbar la confirmación de un pago**: si algo revienta aquí, el
pedido se marca para revisión humana y sigue adelante. Un semáforo roto que detenga
la caja sería peor que no tener semáforo.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.models.crm import Customer
from app.models.portal import PortalOrder

log = logging.getLogger(__name__)
_TZ_CO = ZoneInfo("America/Bogota")

# ── Umbrales, sacados de las ventas REALES de la tienda ──────────────────────
# 2.730 ventas de los últimos 180 días (medido el 8-oct-2026): mediana $53.000,
# p95 $216.700, p99 $345.940. "Valor elevado" aquí significa elevado PARA ESTA
# TIENDA; un umbral inventado marcaría en rojo la compra normal de un bulto.
MONTO_P95 = 220_000
MONTO_P99 = 350_000

# La tienda vende de 8 a 19 (medido). Se deja hasta las 22 porque comprar por web de
# noche es normal; de madrugada no lo es, y es una de las señales de Bold.
HORA_NORMAL_DESDE = 7
HORA_NORMAL_HASTA = 22

#: Rieles donde el pagador se autentica en SU banco: PSE, Nequi, Daviplata, botón de
#: Bancolombia. Ahí no existe "me clonaron la tarjeta", que es el miedo concreto.
#: No los vuelve inofensivos —queda la disputa por "nunca me llegó"— pero el riesgo
#: es de otro orden y marcarlos igual que una tarjeta sería gritar por todo.
MEDIOS_AUTENTICADOS = {"PSE", "NEQUI", "DAVIPLATA", "BANCOLOMBIA", "BOTON_BANCOLOMBIA", "QR"}

ALTO = 50
MEDIO = 25


class Senal:
    """Una señal disparada: cuánto pesa y cómo se le explica a un humano."""

    __slots__ = ("codigo", "puntos", "texto")

    def __init__(self, codigo: str, puntos: int, texto: str) -> None:
        self.codigo, self.puntos, self.texto = codigo, puntos, texto

    def dict(self) -> dict:
        return {"codigo": self.codigo, "puntos": self.puntos, "texto": self.texto}


async def evaluar(db, pedido: PortalOrder, datos: dict) -> tuple[str, int, list[dict]]:
    """Devuelve (nivel, puntaje, señales) para un pedido recién pagado.

    `datos` es el bloque `data` del webhook de Bold, tal cual llega.
    """
    try:
        return await _evaluar(db, pedido, datos)
    except Exception:
        # Jamás dejar que esto tumbe un pago. Si el semáforo falla, que lo mire una
        # persona: es el único desenlace que no pierde plata por ninguno de los dos lados.
        log.exception("RIESGO · falló la evaluación de %s — se marca para revisión",
                      pedido.order_reference)
        return "medio", MEDIO, [{"codigo": "error_motor", "puntos": MEDIO,
                                 "texto": "No se pudo evaluar el riesgo. Revísalo a mano."}]


async def _evaluar(db, pedido: PortalOrder, datos: dict) -> tuple[str, int, list[dict]]:
    senales: list[Senal] = []
    tarjeta = (datos.get("card") or {})
    medio = (datos.get("payment_method") or "").upper()
    tipo_tarjeta = (tarjeta.get("card_type") or "").upper()
    pan = tarjeta.get("masked_pan") or None
    correo = (datos.get("payer_email") or "").strip().lower() or None
    monto = int(pedido.bold_amount or 0)

    # Un pago del datáfono es venta PRESENCIAL (chip o contactless): no es el caso que
    # nos ocupa y no tiene por qué ensuciar el semáforo.
    if (datos.get("integration") or "").upper() == "POS":
        return "bajo", 0, []

    # ── 1. El medio de pago: aquí vive casi todo el riesgo ───────────────────
    if medio == "CARD" and tipo_tarjeta == "CREDIT":
        senales.append(Senal("tarjeta_credito", 15,
                             "Tarjeta de crédito sin presencia física: es el único medio "
                             "donde cabe 'no reconozco esta compra'."))
    elif medio in MEDIOS_AUTENTICADOS:
        senales.append(Senal("medio_autenticado", -20,
                             f"Pagó por {medio}: se autenticó en su propio banco, "
                             "no cabe tarjeta clonada."))

    # ── 2. Monto fuera de lo normal PARA ESTA TIENDA ─────────────────────────
    if monto >= MONTO_P99:
        senales.append(Senal("monto_muy_alto", 30,
                             f"${monto:,.0f} supera el 99% de tus ventas (p99 ${MONTO_P99:,.0f})."
                             .replace(",", ".")))
    elif monto >= MONTO_P95:
        senales.append(Senal("monto_alto", 15,
                             f"${monto:,.0f} está por encima del 95% de tus ventas."
                             .replace(",", ".")))

    # ── 3. Cliente nuevo ─────────────────────────────────────────────────────
    anteriores = 0
    if pedido.customer_id:
        anteriores = int(
            (await db.execute(
                select(func.count()).select_from(PortalOrder).where(
                    PortalOrder.customer_id == pedido.customer_id,
                    PortalOrder.id != pedido.id,
                    PortalOrder.payment_status == "paid",
                )
            )).scalar() or 0
        )
    if anteriores == 0:
        senales.append(Senal("cliente_nuevo", 15,
                             "Primera compra pagada de este cliente."))

    # ── 4. Varios pedidos en muy poco tiempo (señal de Bold) ─────────────────
    if pedido.customer_id:
        desde = datetime.now(_TZ_CO) - timedelta(hours=24)
        recientes = int(
            (await db.execute(
                select(func.count()).select_from(PortalOrder).where(
                    PortalOrder.customer_id == pedido.customer_id,
                    PortalOrder.id != pedido.id,
                    PortalOrder.created_at >= desde,
                )
            )).scalar() or 0
        )
        if recientes >= 2:
            senales.append(Senal("pedidos_en_rafaga", 25,
                                 f"{recientes + 1} pedidos de este cliente en 24 horas."))

    # ── 5. La MISMA tarjeta en clientes distintos ────────────────────────────
    # La más delatora de todas: una tarjeta robada se prueba contra varias identidades.
    if pan:
        otros = (await db.execute(
            select(func.count(func.distinct(PortalOrder.customer_id))).where(
                PortalOrder.bold_masked_pan == pan,
                PortalOrder.customer_id != pedido.customer_id,
            )
        )).scalar() or 0
        if otros >= 1:
            senales.append(Senal("tarjeta_compartida", 40,
                                 f"Esta misma tarjeta ya se usó con {otros} cliente(s) "
                                 "distinto(s). Verifica antes de entregar."))

    # ── 6. Varias tarjetas distintas para el mismo cliente (señal de Bold) ───
    if pedido.customer_id:
        desde = datetime.now(_TZ_CO) - timedelta(days=7)
        tarjetas = (await db.execute(
            select(func.count(func.distinct(PortalOrder.bold_masked_pan))).where(
                PortalOrder.customer_id == pedido.customer_id,
                PortalOrder.bold_masked_pan.isnot(None),
                PortalOrder.created_at >= desde,
            )
        )).scalar() or 0
        if tarjetas >= 3:
            senales.append(Senal("muchas_tarjetas", 30,
                                 f"{tarjetas} tarjetas distintas de un mismo cliente en 7 días."))

    # ── 7. Horario inusual (señal de Bold) ───────────────────────────────────
    hora = datetime.now(_TZ_CO).hour
    if not (HORA_NORMAL_DESDE <= hora < HORA_NORMAL_HASTA):
        senales.append(Senal("horario_inusual", 15,
                             f"Pago a las {hora}:00, fuera del horario en que vendes."))

    # ── 8. Fuera de la zona de reparto ───────────────────────────────────────
    direccion = (pedido.shipping_address or "").lower()
    if direccion and not any(c in direccion for c in ("pereira", "dosquebradas")):
        senales.append(Senal("fuera_de_cobertura", 20,
                             "La dirección no menciona Pereira ni Dosquebradas."))

    # ── 9. El correo del pagador no es el del cliente ────────────────────────
    if correo and pedido.customer_id:
        cli = (await db.execute(
            select(Customer.email).where(Customer.id == pedido.customer_id)
        )).scalar_one_or_none()
        if cli and cli.strip().lower() != correo:
            senales.append(Senal("correo_distinto", 10,
                                 f"Pagó desde {correo}, distinto del correo del cliente."))

    puntaje = max(0, sum(s.puntos for s in senales))
    # Un riel autenticado no puede terminar en rojo por sumar señales menores: el
    # fraude que nos preocupa (tarjeta ajena) ahí no cabe.
    tope_medio = medio in MEDIOS_AUTENTICADOS
    if puntaje >= ALTO and not tope_medio:
        nivel = "alto"
    elif puntaje >= MEDIO:
        nivel = "medio"
    else:
        nivel = "bajo"

    return nivel, puntaje, [s.dict() for s in senales]


def extraer_senales(datos: dict) -> dict:
    """Saca del evento de Bold los campos que hay que guardar en columnas.

    Van a columnas y no al JSON porque una señal que no se puede cruzar con un WHERE
    no detecta nada: lo que delata un fraude es ver la misma tarjeta en dos clientes.
    """
    tarjeta = datos.get("card") or {}
    cuotas = tarjeta.get("installments")
    return {
        "bold_payment_method": (datos.get("payment_method") or None),
        "bold_integration": (datos.get("integration") or None),
        "bold_card_type": (tarjeta.get("card_type") or None),
        "bold_card_brand": (tarjeta.get("brand") or None),
        "bold_masked_pan": (tarjeta.get("masked_pan") or None),
        # Bold enmascara el correo en algunos canales ("XXXX@XXX.XX"): eso no es un
        # correo y guardarlo solo ensucia el cruce.
        "bold_payer_email": (
            c if (c := (datos.get("payer_email") or "").strip().lower())
            and "xxx" not in c else None
        ),
        "bold_installments": int(cuotas) if isinstance(cuotas, int) else None,
    }
