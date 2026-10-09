"""¿Esta dirección está de verdad en la zona de reparto? Se decide AQUÍ, en el servidor.

Diego (9-oct-2026): *"solo despachamos para Pereira y Dosquebradas, verificando la
dirección por la API de Maps"*.

EL HUECO QUE CIERRA
El checkout ya bloqueaba el cobro anticipado fuera de 15 km, pero **esos 15 km los
calculaba el navegador y los mandaba en el cuerpo de la petición**. El servidor se los
creía. Un `km: 1` escrito a mano habilitaba el cobro de un pedido a 400 km, y el peor
fallo posible de esta integración —cobrar sin poder entregar— quedaba a un dedo.

Ahora el servidor hace dos cosas que el navegador no puede falsear:

1. **Recalcula la distancia** a partir de las coordenadas. Es gratis y no depende de
   ninguna API: la fórmula del haversine contra el pin oficial de la ficha.
2. **Geocodifica la dirección escrita** con la API de Google y comprueba que exista,
   que esté en Pereira o Dosquebradas, y que caiga dentro del radio.

LA TRAMPA QUE SE DESCUBRIÓ PROBANDO
Una dirección inventada —`"jkashdkjashd 123 no existe"`— **también devuelve `OK`**.
Google no falla: responde con el centroide del país y `location_type: APPROXIMATE`.
Si uno solo mira el `status`, acepta cualquier cosa. Por eso se rechaza explícitamente
`APPROXIMATE`: una dirección a la que Google no sabe llegar tampoco sabe llegar el
domiciliario.

LO QUE **NO** HACE
No rechaza pedidos. Un pedido fuera de zona entra igual y se cierra por WhatsApp, como
siempre. Lo único que se niega es **cobrar por adelantado**, que es lo irreversible.
"""

from __future__ import annotations

import logging
import math
import os
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

log = logging.getLogger(__name__)

#: Pin oficial de la ficha de Google. El mismo que usa la tienda en `lib/delivery.ts`:
#: si los dos no coinciden, el cliente ve un domicilio y se le cobra otro.
LOCAL_LAT, LOCAL_LNG = 4.8266652, -75.6923926

RADIO_MAX_KM = 15.0

#: Los dos municipios que se reparten. Se comparan sin tildes ni mayúsculas porque
#: Google devuelve "Bogotá" con tilde y "Dosquebradas" sin ella, y un acento no puede
#: decidir si una venta se cobra.
MUNICIPIOS = {"pereira", "dosquebradas"}

#: Precisión que Google le da al resultado. `APPROXIMATE` significa "no encontré esto,
#: te doy la zona": sirve para un mapa, no para mandar un domicilio.
PRECISION_INSUFICIENTE = {"APPROXIMATE"}

#: Si la dirección escrita y las coordenadas del navegador se contradicen por más de
#: esto, algo no cuadra: o el GPS está en otra parte, o alguien escribió una dirección
#: distinta de donde está. En la duda no se cobra por adelantado.
DISCREPANCIA_MAX_KM = 3.0

#: SE GUARDA LA GEOCODIFICACIÓN, NO EL VEREDICTO.
#:
#: Guardar el veredicto parecía lo natural y estaba mal: el veredicto depende de la
#: dirección **y** de las coordenadas del cliente, así que el segundo pedido a la misma
#: dirección recibía el fallo del primero. Lo cazó la prueba de la trampa —dirección de
#: Dosquebradas con GPS en Bogotá— que salió "cobrable" porque reusó la respuesta de un
#: caso anterior.
#:
#: Lo que sí depende solo de la dirección es lo que contesta Google. Eso se guarda; el
#: veredicto se vuelve a calcular siempre.
_TTL = 86_400
_cache: dict[str, tuple[float, dict | None]] = {}


def distancia_km(lat: float, lng: float) -> float:
    """Línea recta hasta el local (haversine). Gratis y sin depender de nadie."""
    r = 6371.0
    dlat = math.radians(lat - LOCAL_LAT)
    dlng = math.radians(lng - LOCAL_LNG)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(LOCAL_LAT)) * math.cos(math.radians(lat))
         * math.sin(dlng / 2) ** 2)
    return r * 2 * math.asin(math.sqrt(a))


@dataclass
class Verificacion:
    """El veredicto. `cobrable` es lo único que decide si se permite pagar en línea."""

    cobrable: bool
    motivo: str = ""
    km: float | None = None
    municipio: str | None = None
    direccion_normalizada: str | None = None
    precision: str | None = None
    #: De dónde salió la distancia: 'geocodificada' (verificada por Google),
    #: 'coordenadas' (recalculada en el servidor desde el GPS) o 'sin_dato'.
    fuente: str = "sin_dato"
    verificada_por_google: bool = False

    def dict(self) -> dict:
        return {
            "cobrable": self.cobrable, "motivo": self.motivo, "km": self.km,
            "municipio": self.municipio, "direccion": self.direccion_normalizada,
            "precision": self.precision, "fuente": self.fuente,
            "verificada_por_google": self.verificada_por_google,
        }


def _sin_tildes(s: str) -> str:
    tabla = str.maketrans("áéíóúÁÉÍÓÚàèìòùÀÈÌÒÙ", "aeiouAEIOUaeiouAEIOU")
    return s.translate(tabla).strip().lower()


async def _geocodificar(direccion: str) -> dict | None:
    """Pregunta a Google dónde queda esta dirección. Devuelve None si no se pudo.

    Nunca lanza: si Google no contesta, el checkout cae al camino conservador
    (coordenadas del navegador recalculadas) en vez de romperse.
    """
    key = os.environ.get("GBP_PLACES_API_KEY") or ""
    if not key:
        log.warning("COBERTURA · sin GBP_PLACES_API_KEY: no se puede verificar la dirección")
        return None

    url = "https://maps.googleapis.com/maps/api/geocode/json?" + urlencode({
        "address": direccion,
        # Limita la búsqueda a Colombia: sin esto, "Calle 15" puede caer en España.
        "components": "country:CO",
        "region": "co",
        "language": "es",
        "key": key,
    })
    try:
        async with httpx.AsyncClient(timeout=8) as cli:
            r = await cli.get(url)
        if r.status_code != 200:
            log.warning("COBERTURA · geocoding HTTP %s", r.status_code)
            return None
        datos = r.json() or {}
        if datos.get("status") != "OK" or not datos.get("results"):
            log.info("COBERTURA · geocoding devolvió %s para %r",
                     datos.get("status"), direccion[:60])
            return None
        return datos["results"][0]
    except Exception:
        log.exception("COBERTURA · falló el geocoding")
        return None


def _municipio_de(resultado: dict) -> str | None:
    for comp in resultado.get("address_components", []):
        tipos = comp.get("types", [])
        if "locality" in tipos or "administrative_area_level_2" in tipos:
            return comp.get("long_name")
    return None


async def verificar(
    direccion: str | None, lat: float | None, lng: float | None
) -> Verificacion:
    """El veredicto sobre si a esta dirección se le puede cobrar por adelantado.

    El orden importa: primero se intenta verificar la dirección CON Google, porque es
    lo único que no se puede falsear desde el navegador. Si Google no contesta, se cae
    a recalcular la distancia desde las coordenadas — que sigue siendo mejor que creerle
    al `km` del cuerpo, porque al menos la cuenta la hace el servidor.
    """
    texto = (direccion or "").strip()

    # ── 1. La dirección escrita, verificada por Google ───────────────────────
    if len(texto) >= 8:
        clave = _sin_tildes(texto)
        ahora = time.monotonic()
        guardado = _cache.get(clave)
        if guardado and ahora - guardado[0] < _TTL:
            g = guardado[1]
        else:
            g = await _geocodificar(texto)
            _cache[clave] = (ahora, g)

        if g:
            precision = g.get("geometry", {}).get("location_type")
            loc = g.get("geometry", {}).get("location") or {}
            glat, glng = loc.get("lat"), loc.get("lng")
            municipio = _municipio_de(g)
            km = distancia_km(glat, glng) if glat is not None and glng is not None else None

            v = Verificacion(
                cobrable=False, km=round(km, 2) if km is not None else None,
                municipio=municipio, direccion_normalizada=g.get("formatted_address"),
                precision=precision, fuente="geocodificada", verificada_por_google=True,
            )

            if precision in PRECISION_INSUFICIENTE:
                # Google no encontró la dirección: devolvió "por ahí". Un domiciliario
                # tampoco la encontraría.
                v.motivo = ("No pudimos ubicar esa dirección con exactitud. Revísala o "
                            "escríbenos por WhatsApp y la confirmamos contigo.")
            elif municipio and _sin_tildes(municipio) not in MUNICIPIOS:
                v.motivo = (f"Repartimos solo en Pereira y Dosquebradas, y esa dirección "
                            f"está en {municipio}. Escríbenos por WhatsApp: coordinamos el "
                            "envío y te decimos el costo antes de cobrarte.")
            elif km is None or km > RADIO_MAX_KM:
                v.motivo = (f"Tu dirección está a {km:.1f} km del local, fuera de nuestra "
                            "zona de reparto. Escríbenos por WhatsApp: coordinamos el envío "
                            "contigo y te decimos el costo antes de cobrarte."
                            if km is not None else "No pudimos calcular la distancia.")
            elif (lat is not None and lng is not None
                  and distancia_km(lat, lng) is not None
                  and abs(distancia_km(lat, lng) - km) > DISCREPANCIA_MAX_KM):
                # La dirección escrita y el GPS no hablan del mismo sitio.
                v.motivo = ("La dirección que escribiste y tu ubicación no coinciden. "
                            "Escríbenos por WhatsApp y lo confirmamos.")
                log.warning("COBERTURA · discrepancia: escrita %.1f km vs GPS %.1f km",
                            km, distancia_km(lat, lng))
            else:
                v.cobrable = True

            return v

    # ── 2. Sin dirección verificable: la cuenta la hace el SERVIDOR ──────────
    if lat is not None and lng is not None:
        km = round(distancia_km(lat, lng), 2)
        if km > RADIO_MAX_KM:
            return Verificacion(
                cobrable=False, km=km, fuente="coordenadas",
                motivo=(f"Tu ubicación está a {km:.1f} km del local, fuera de nuestra zona "
                        "de reparto en Pereira y Dosquebradas. Escríbenos por WhatsApp: "
                        "coordinamos el envío contigo y te decimos el costo antes de cobrarte."),
            )
        return Verificacion(cobrable=True, km=km, fuente="coordenadas")

    # ── 3. Ni dirección ni coordenadas: no se cobra a ciegas ─────────────────
    return Verificacion(
        cobrable=False, fuente="sin_dato",
        motivo=("Necesitamos tu dirección o tu ubicación para poder cobrarte el domicilio "
                "correcto. Escríbenos por WhatsApp y lo coordinamos."),
    )
