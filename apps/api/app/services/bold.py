"""Motor de pagos con Bold. Lo usan POR IGUAL la tienda web y el portal.

Diego (4-oct-2026): *"por el portal de clientes también habilitamos los pagos, que
deje opción para pedido o contraentrega, hablamos el mismo idioma en web y en el
portal"*. Por eso aquí no hay ni una palabra sobre canales: este módulo sabe de
firmas, de webhooks y de la API de Bold, y nada más. Quien lo llama decide si el
pedido venía de `/checkout` o del portal, y la única diferencia visible es el
prefijo de la referencia.

LAS TRES COSAS QUE NO SE PUEDEN HACER MAL
-----------------------------------------
1. **El monto que se firma lo calcula el servidor.** Este módulo recibe un entero y
   firma ese entero. Si alguna vez ese número viene del navegador, la integración
   entera deja de servir: cualquiera compraría un bulto de concentrado por $1.000.
2. **La llave secreta no sale de aquí.** No se escribe en logs, no se devuelve en
   respuestas, no viaja al cliente. Lo que sí viaja es la de identidad, que está
   hecha para eso.
3. **La firma se compara en tiempo constante.** `hmac.compare_digest` y nunca `==`:
   una comparación normal se corta en el primer byte distinto y el tiempo que tarda
   filtra, byte a byte, cuál era la firma correcta.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime
from typing import Literal

import httpx

log = logging.getLogger(__name__)

BOLD_ENV = os.getenv("BOLD_ENV", "sandbox").strip().lower()
IDENTITY_KEY = os.getenv("BOLD_IDENTITY_KEY", "").strip()
SECRET_KEY = os.getenv("BOLD_SECRET_KEY", "").strip()
# CONFIRMADO en la documentación oficial (developers.bold.co/webhook, 4-oct-2026):
# el webhook lo firma la **llave secreta** de las llaves de integración, no la de
# identidad. Por eso aquí el valor por defecto es SECRET_KEY y no una cadena vacía.
#
# Se mantiene configurable y se siguen probando varias candidatas porque la propia
# documentación añade que "Bold selecciona la llave según la prioridad del método de
# pago" — una frase lo bastante vaga como para no jugársela a una sola.
WEBHOOK_SECRET = os.getenv("BOLD_WEBHOOK_SECRET", "").strip()

API_BASE = "https://payments.api.bold.co"
DIVISA = "COP"

#: Minutos que un pedido espera el pago antes de darse por vencido.
MINUTOS_PARA_PAGAR = 30


def esta_configurado() -> bool:
    """¿Hay llaves? Sin esto el checkout debe ofrecer solo contraentrega."""
    return bool(IDENTITY_KEY and SECRET_KEY)


def nueva_referencia(canal: Literal["web", "portal"], ahora: datetime) -> str:
    """Referencia única del pedido, la que viaja a Bold como `orderId`.

    Formato `BPW-20261005-a3f9c201` (web) o `BPP-…` (portal). Son 21 caracteres,
    muy por debajo del tope de 60 de Bold.

    Los 8 hex NO son decorativos: la referencia viaja en la URL de la página de
    confirmación y en el enlace de pago. Si fuera un consecutivo, cualquiera
    restaría uno y miraría el pedido del vecino. Con 4 bytes de `secrets` hay 4.294
    millones de combinaciones por día, que no se adivinan a fuerza bruta.
    """
    prefijo = "BPW" if canal == "web" else "BPP"
    return f"{prefijo}-{ahora:%Y%m%d}-{secrets.token_hex(4)}"


def firma_integridad(referencia: str, monto: int, divisa: str = DIVISA) -> str:
    """Firma que Bold exige para aceptar el cobro. SHA-256, no HMAC.

    El orden es exactamente **OrderId + Monto + Divisa + LlaveSecreta**, pegados sin
    separador. El monto va **sin decimales ni separadores de miles**: `76000`, jamás
    `76.000` ni `76000.00`.

    Un error de un solo carácter aquí no da un mensaje de error: Bold rechaza el
    cobro en silencio, y es el fallo más común de esta integración. Por eso el monto
    entra como `int` y no como `Decimal` ni `str`: el tipo impide el error.
    """
    if not isinstance(monto, int) or isinstance(monto, bool):
        raise TypeError("El monto debe ser un entero de pesos, sin decimales")
    if monto <= 0:
        raise ValueError("El monto debe ser mayor que cero")
    cadena = f"{referencia}{monto}{divisa}{SECRET_KEY}"
    return hashlib.sha256(cadena.encode("utf-8")).hexdigest()


def _firma_webhook(raw_body: bytes, llave: str) -> str:
    """HMAC-SHA256 sobre el cuerpo crudo **codificado en base64**.

    Ojo con el doble paso: Bold no firma el cuerpo, firma su base64. Y tiene que ser
    el cuerpo CRUDO, en bytes, tal como llegó. Si se deserializa el JSON y se vuelve
    a serializar, cambian los espacios y el orden de las llaves, y la firma no
    coincide nunca — el error clásico de esta validación en FastAPI.
    """
    return hmac.new(llave.encode("utf-8"), base64.b64encode(raw_body), hashlib.sha256).hexdigest()


def verificar_webhook(raw_body: bytes, firma_recibida: str) -> tuple[bool, str]:
    """¿El webhook viene de Bold? Devuelve `(es_valido, con_qué_llave)`.

    El algoritmo está tomado literal de la documentación oficial: base64 del cuerpo
    crudo → HMAC-SHA256 con la llave → hexadecimal → comparar con `x-bold-signature`.

    **Qué llave:** la documentación dice que firma la **llave secreta**, y por eso es
    la primera candidata. Pero añade que "Bold selecciona la llave según la prioridad
    del método de pago", así que se siguen probando varias y se devuelve cuál
    funcionó: con una frase así, apostar a una sola sería construir sobre arena.

    Probar varias no debilita nada: una firma falsa no coincide con ninguna. Lo
    inseguro sería aceptar sin comprobar, no comprobar de más.

    **En modo pruebas Bold firma con la clave vacía**, tal cual lo dice la
    documentación, así que esa también es candidata — y solo fuera de producción,
    porque en producción aceptar una firma hecha con llave vacía sería dejar la
    puerta abierta de par en par.
    """
    if not firma_recibida:
        return False, "sin-firma"

    candidatas: list[tuple[str, str]] = []
    if WEBHOOK_SECRET:
        candidatas.append(("configurada", WEBHOOK_SECRET))
    # La documentada. Va primero para que el caso normal acierte al primer intento.
    candidatas.append(("secreta", SECRET_KEY))
    candidatas.append(("identidad", IDENTITY_KEY))
    if BOLD_ENV != "production":
        candidatas.append(("vacia-sandbox", ""))

    for nombre, llave in candidatas:
        if not llave and nombre != "vacia-sandbox":
            continue
        if hmac.compare_digest(_firma_webhook(raw_body, llave), firma_recibida):
            if nombre != "configurada":
                # No es un detalle: es el dato que cierra la pregunta abierta de la
                # integración. Se registra bien visible para no perderlo.
                log.warning(
                    "BOLD · el webhook valida con la llave '%s'. Ponla en "
                    "BOLD_WEBHOOK_SECRET y anótalo en docs/BOLD_INTEGRATION.md",
                    nombre,
                )
            return True, nombre

    return False, "ninguna"


async def consultar_voucher(referencia: str) -> dict:
    """Pregunta a Bold, servidor contra servidor, cómo quedó un pago.

    Es la red de seguridad de la conciliación: si un webhook se pierde —y se pierden,
    por un despliegue a destiempo o una caída de red—, esto es lo que evita que un
    pedido PAGADO se quede marcado como pendiente y el cliente no reciba nada.

    Aquí va la llave de **IDENTIDAD**, no la secreta. Verificado el 4-oct-2026
    contra la API real: con la de identidad responde 404 "referencia no encontrada"
    (o sea, autentica bien), y con la secreta responde 403. No son intercambiables.

    Estados que devuelve Bold: PROCESSING, PENDING (solo PSE), APPROVED, REJECTED,
    FAILED, VOIDED, NO_TRANSACTION_FOUND.
    """
    url = f"{API_BASE}/v2/payment-voucher/{referencia}"
    async with httpx.AsyncClient(timeout=20) as cliente:
        r = await cliente.get(url, headers={"Authorization": f"x-api-key {IDENTITY_KEY}"})

    if r.status_code == 404:
        # Bold aún no conoce la referencia: el cliente nunca llegó a pagar.
        return {"estado": "NO_TRANSACTION_FOUND", "http": 404}
    if r.status_code != 200:
        # Nunca se registra el cuerpo entero sin mirar: podría traer datos del
        # pagador. Con el código de estado basta para diagnosticar.
        log.error("BOLD · voucher %s respondió HTTP %s", referencia, r.status_code)
        return {"estado": "ERROR", "http": r.status_code}

    datos = r.json() or {}
    payload = datos.get("payload") or datos
    # EL CAMPO SE LLAMA `payment_status`, Y NINGÚN OTRO.
    #
    # Hasta el 9-oct-2026 esto leía `status` o `transaction_status`, que Bold no
    # manda: el estado SIEMPRE salía "DESCONOCIDO" y la conciliación no entraba en
    # ninguna de sus ramas. O sea, **la red de seguridad nunca funcionó**: ni rescataba
    # un pago cuyo webhook se hubiera perdido, ni vencía un enlace que nadie pagó.
    #
    # Se descubrió por el síntoma más tonto: a Diego le sonaba un aviso de "pedido
    # pendiente" que no existía. Era un enlace de prueba suyo, sin pagar, que llevaba
    # un día entero sin poder vencerse.
    #
    # Verificado contra la API real con cuatro referencias: `payment_status` vale
    # APPROVED en el pago de Mabel y NO_TRANSACTION_FOUND en los no pagados;
    # `status` y `transaction_status` vienen vacíos SIEMPRE.
    estado = (
        payload.get("payment_status")
        or payload.get("status")
        or payload.get("transaction_status")
        or "DESCONOCIDO"
    )
    return {
        "estado": str(estado).upper(),
        # Bold lo llama `transaction_id` en el voucher, no `payment_id`.
        "payment_id": (payload.get("transaction_id") or payload.get("payment_id")
                       or payload.get("id")),
        "monto": payload.get("total") or payload.get("amount"),
        "http": 200,
        "crudo": payload,
    }


def enmascarar(valor: str | None) -> str:
    """Para los logs: deja ver que hay algo, no qué es.

    Toda llave o firma que termine en un log pasa por aquí. Un secreto en los logs
    es un secreto filtrado: los logs se copian, se mandan por chat y se guardan en
    sitios que nadie audita.
    """
    if not valor:
        return "(vacío)"
    if len(valor) <= 8:
        return "*" * len(valor)
    return f"{valor[:4]}…{valor[-2:]} ({len(valor)} car.)"
