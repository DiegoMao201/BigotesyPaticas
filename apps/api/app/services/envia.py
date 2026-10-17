"""Envíos nacionales por transportadora, a través de Envia.com (16-oct-2026).

Diego: *"quiero hacer envíos fuera de mi cobertura local que es Pereira y
Dosquebradas [...] el cliente mira cuánto le cuesta el envío y lo paga de una vez
[...] aprobamos la venta y así se genera la guía que le llega al cliente, la guía al
proveedor para la recogida o nosotros llevamos el paquete al punto"*.

Este módulo habla SOLO con Envia: cotiza, genera guías, rastrea, cancela y programa
recogidas. No sabe de pedidos ni de Bold; quien lo llama decide qué hacer con lo que
devuelve. No importa FastAPI a propósito, para poder probarlo suelto contra el
ambiente de pruebas sin levantar la API.

LO QUE SE APRENDIÓ PROBANDO CONTRA EL SANDBOX (16-oct-2026)
------------------------------------------------------------
- **La ciudad va como código DANE de 8 dígitos, no como nombre.** `POST /locate`
  (sin token) lo resuelve: Dosquebradas → `66170000`, Bogotá → `11001000`,
  Medellín → `05001000`. Con el nombre a secas, las transportadoras colombianas
  responden "No existe tarifa para la ruta".
- **Una petición de tarifa = una transportadora.** No hay "todas": se pregunta a
  cada una en paralelo y se juntan las respuestas. Las que no cubren la ruta
  devuelven error (TCC a Bogotá desde Dosquebradas, por ejemplo) y se ignoran.
- **El departamento va con el código de 2 letras** de la lista de Envia (`RI`,
  `DC`, `AN`…), que NO coincide con el ISO ni con el de Shopify.
- **Generar una guía descuenta saldo de la cuenta de Envia** y cancelarla antes
  de que la transportadora la recoja lo devuelve (`balanceReturned`). El PDF de
  la etiqueta queda en una URL pública de S3.
- El token de pruebas solo sirve en `api-test.envia.com`; el de producción solo en
  `api.envia.com`. Mezclarlos da un 401 en texto plano.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re
import time
from dataclasses import asdict, dataclass

import httpx

log = logging.getLogger(__name__)

TOKEN = os.getenv("ENVIA_TOKEN", "").strip()
ENV = os.getenv("ENVIA_ENV", "test").strip().lower()
_TEST = ENV != "production"
API = "https://api-test.envia.com" if _TEST else "https://api.envia.com"
QUERIES = "https://queries.test.envia.com" if _TEST else "https://queries.envia.com"
GEOCODES = "https://geocodes.envia.com"

#: Transportadoras a las que se les pide tarifa. Se puede cambiar por variable de
#: entorno sin desplegar código. Las de mensajería urbana (cabify, treggo…) no
#: aplican para envíos entre ciudades.
CARRIERS = [
    c.strip()
    for c in os.getenv("ENVIA_CARRIERS", "coordinadora,serviEntrega,interRapidisimo,tcc").split(",")
    if c.strip()
]

NOMBRES = {
    "coordinadora": "Coordinadora",
    "serviEntrega": "Servientrega",
    "interRapidisimo": "Inter Rapidísimo",
    "tcc": "TCC",
    "envia": "Envia",
    "dhl": "DHL",
    "fedex": "FedEx",
    "jtexpress": "J&T Express",
    "redServi": "RedServi",
    "saferbo": "Saferbo",
}

#: Recargo sobre la tarifa de la transportadora, en porcentaje. 0 = se cobra lo
#: que cobra Envia, redondeado hacia arriba a la centena.
MARGEN_PCT = float(os.getenv("ENVIA_MARGEN_PCT", "0") or 0)

#: Departamentos de Colombia con el código que Envia espera en `state`. Copiados
#: de `GET /state?country_code=CO` el 16-oct-2026 (Bogotá y Cundinamarca vienen
#: repetidos allá; aquí van una vez).
DEPARTAMENTOS: list[tuple[str, str]] = [
    ("AM", "Amazonas"), ("AN", "Antioquia"), ("AR", "Arauca"), ("AT", "Atlántico"),
    ("DC", "Bogotá D.C."), ("BL", "Bolívar"), ("BY", "Boyacá"), ("CL", "Caldas"),
    ("CA", "Caquetá"), ("CS", "Casanare"), ("CU", "Cauca"), ("CE", "Cesar"),
    ("CH", "Chocó"), ("CO", "Córdoba"), ("CN", "Cundinamarca"), ("GU", "Guainía"),
    ("GA", "Guaviare"), ("HU", "Huila"), ("LG", "La Guajira"), ("MA", "Magdalena"),
    ("ME", "Meta"), ("NA", "Nariño"), ("NS", "Norte de Santander"), ("PU", "Putumayo"),
    ("QU", "Quindío"), ("RI", "Risaralda"), ("SA", "San Andrés y Providencia"),
    ("SN", "Santander"), ("SU", "Sucre"), ("TO", "Tolima"), ("VC", "Valle del Cauca"),
    ("VA", "Vaupés"), ("VI", "Vichada"),
]
DEPARTAMENTO_NOMBRE = dict(DEPARTAMENTOS)

#: Lo que la transportadora ve como remitente. Es la ficha de Google: misma
#: dirección, mismo teléfono. El documento (NIT o cédula) va por variable de
#: entorno porque no está escrito en ningún otro sitio del código.
#:
#: EL RESPONSABLE DEL ENVÍO ES BIGOTES Y PATICAS (Diego, 16-oct-2026): así figura
#: como remitente en la guía. Si la transportadora necesita más información, el
#: contacto es Diego Mauricio García Rengifo, representante legal (CC 1088266407,
#: en ENVIA_ORIGIN_DOC); va en la referencia.
ORIGEN = {
    "name": "Bigotes y Paticas",
    "company": "Bigotes y Paticas",
    "email": "bigotesypaticasdosquebradas@gmail.com",
    "phone": "3206876633",
    "phone_code": "CO",
    "street": "Calle 15",
    "number": "3A-07",
    "district": "Samara Plaza Mall, Local 2",
    "city": "66170000",  # Dosquebradas, código DANE (POST /locate)
    "state": "RI",
    "country": "CO",
    "postalCode": "661001",
    "reference": "Samara Plaza Mall, Local 2 · Contacto: Diego Mauricio García Rengifo, representante legal",
    "coordinates": {"latitude": "4.8266652", "longitude": "-75.6923926"},
}
_ORIGEN_DOC = os.getenv("ENVIA_ORIGIN_DOC", "").strip()
if _ORIGEN_DOC:
    ORIGEN["identificationNumber"] = _ORIGEN_DOC


class EnviaError(Exception):
    """Envia contestó con error o no contestó. El mensaje ya viene en palabras."""


def esta_configurado() -> bool:
    return bool(TOKEN)


# ══════════════════════════════════════════════════════════════════════════════
# Peso y empaque
# ══════════════════════════════════════════════════════════════════════════════

_UNIDAD = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(kg|kl|kilo|kilos|k|g|gr|grs|gramos|lb|lbs|libras?|oz|onzas?|ml|l|lt|litros?)\b",
    re.IGNORECASE,
)
_MULTI = re.compile(r"(\d+)\s*x\s*(\d+(?:[.,]\d+)?)\s*(kg|g|gr|grs|ml|l|oz)\b", re.IGNORECASE)
#: "Bravecto 10-20 Kg", "Nexgard 25 - 50 Kg", "Spectra 2 A 3.5 Kg": es el peso del
#: PERRO, no del producto. Si el nombre trae un rango así, los kilos no cuentan.
_RANGO_ANIMAL = re.compile(r"\d+(?:[.,]\d+)?\s*(?:-|a|hasta)\s*\d+(?:[.,]\d+)?\s*(?:kg|k)\b", re.IGNORECASE)

PESO_POR_DEFECTO_KG = 0.5


def peso_kg_de(nombre: str, atributos: dict | None = None) -> float:
    """Peso de UNA unidad, en kilos.

    MANDA `attributes.peso_kg`: el 16-oct-2026 se les puso a los 546 productos
    publicados (scripts/pesos_productos.py), así que el nombre es solo el respaldo
    para productos nuevos. Del nombre se toma la cifra MÁS GRANDE que aparezca,
    convertida a kilos: en "3,5 Lb (1,59 Kg)" gana 1,59 kg y no 3,5 lb. Los
    rangos de peso del animal ("Bravecto 10-20 Kg") se ignoran.
    """
    if atributos:
        for k in ("peso_kg", "weight_kg", "peso"):
            v = atributos.get(k)
            try:
                if v is not None and float(v) > 0:
                    return float(v)
            except (TypeError, ValueError):
                pass

    candidatos: list[float] = []
    texto = nombre or ""
    rango_animal = bool(_RANGO_ANIMAL.search(texto))
    for cant, val, unidad in _MULTI.findall(texto):
        candidatos.append(int(cant) * _a_kg(float(val.replace(",", ".")), unidad))
    for val, unidad in _UNIDAD.findall(texto):
        if rango_animal and unidad.lower() in ("kg", "k", "kl", "kilo", "kilos"):
            continue
        candidatos.append(_a_kg(float(val.replace(",", ".")), unidad))
    candidatos = [c for c in candidatos if 0 < c <= 60]
    return round(max(candidatos), 3) if candidatos else PESO_POR_DEFECTO_KG


def _a_kg(valor: float, unidad: str) -> float:
    u = unidad.lower()
    if u in ("kg", "kl", "kilo", "kilos", "k", "l", "lt", "litro", "litros"):
        return valor
    if u in ("g", "gr", "grs", "gramos", "ml"):
        return valor / 1000
    if u.startswith("lb") or u.startswith("libra"):
        return valor * 0.4536
    if u.startswith("oz") or u.startswith("onza"):
        return valor * 0.02835
    return valor


#: CÓMO SE EMPACA (acordado con Diego, 16-oct-2026).
#:
#: Un bulto de concentrado de 7 kg o más viaja TAL CUAL: el saco es el empaque, se
#: le pone una bolsa plástica o vinipel por fuera para protegerlo y la etiqueta va
#: pegada encima con cinta ancha. No se mete en caja (una caja de 25 kg sale más
#: cara por volumen y no aguanta). Por eso un saco es SU PROPIO paquete, con las
#: medidas de un saco y no de una caja.
#:
#: Lo demás (bolsas de 1,5-3 kg, latas, snacks, medicamentos, accesorios) va junto
#: en UNA caja de cartón con relleno. Si el pedido es un saco + cosas sueltas, son
#: dos paquetes en la misma guía: a un saco no se le puede pegar nada encima.
#:
#: Las transportadoras cobran por el mayor entre el peso real y el volumétrico
#: (largo x ancho x alto / 2.500 en Colombia), así que las medidas importan tanto
#: como los kilos.
SACO_DESDE_KG = 7.0
#: (tope de kilos, largo, ancho, alto) de un saco de concentrado de ese peso.
_SACOS = [
    (8.0, (50, 32, 12)),
    (10.5, (55, 35, 13)),
    (13.0, (60, 38, 14)),
    (16.0, (65, 40, 15)),
    (21.0, (70, 42, 17)),
    (26.0, (75, 45, 18)),
    (60.0, (85, 50, 22)),
]
#: (tope de kilos, largo, ancho, alto) de la caja para lo suelto.
_CAJAS = [
    (0.6, (20, 15, 10)),
    (1.5, (25, 20, 12)),
    (3.5, (35, 25, 15)),
    (6.0, (40, 30, 20)),
    (10.0, (45, 35, 25)),
    (15.0, (50, 40, 30)),
    (25.0, (60, 40, 35)),
]
PESO_MAX_CAJA_KG = 20.0
EMPAQUE_SACO_KG = 0.3


def _dims(tabla: list, kg: float) -> tuple[int, int, int]:
    return next((d for tope, d in tabla if kg <= tope), tabla[-1][1])


def empacar(items: list[dict], valor_declarado: int) -> list[dict]:
    """Convierte los ítems del pedido en los `packages` que pide Envia.

    `items`: [{"nombre", "cantidad", "atributos"?}]. Cada saco de 7 kg o más es un
    paquete; el resto va en una caja (o varias si pasa de 20 kg). El valor
    declarado de la compra se reparte entre los paquetes en proporción al peso.
    """
    sacos: list[tuple[str, float]] = []
    sueltos: list[tuple[str, float]] = []
    for i in items:
        nombre = i.get("nombre", "")
        peso = peso_kg_de(nombre, i.get("atributos"))
        for _ in range(int(i.get("cantidad", 1))):
            (sacos if peso >= SACO_DESDE_KG else sueltos).append((nombre, peso))

    paquetes: list[dict] = []
    for nombre, peso in sacos:
        kg = round(peso + EMPAQUE_SACO_KG, 2)
        paquetes.append({"content": nombre[:60], "weight": kg, "dims": _dims(_SACOS, kg)})

    if sueltos:
        peso_sueltos = sum(p for _, p in sueltos)
        # +10 % de caja y relleno, nunca menos de 300 g.
        kg_total = round(max(peso_sueltos * 1.10, peso_sueltos + 0.3), 2)
        n_cajas = max(1, math.ceil(kg_total / PESO_MAX_CAJA_KG))
        por_caja = round(kg_total / n_cajas, 2)
        nombres: dict[str, int] = {}
        for nombre, _ in sueltos:
            nombres[nombre] = nombres.get(nombre, 0) + 1
        contenido = ", ".join(f"{n[:35]} x{c}" for n, c in nombres.items())[:120]
        for _ in range(n_cajas):
            paquetes.append({"content": contenido, "weight": por_caja, "dims": _dims(_CAJAS, por_caja)})

    if not paquetes:
        paquetes.append({"content": "Productos para mascotas", "weight": 1.0, "dims": _dims(_CAJAS, 1.0)})

    peso_total = sum(p["weight"] for p in paquetes) or 1.0
    salida = []
    repartido = 0
    for n, p in enumerate(paquetes):
        if n == len(paquetes) - 1:
            valor = max(0, int(valor_declarado) - repartido)
        else:
            valor = int(round(valor_declarado * p["weight"] / peso_total))
            repartido += valor
        largo, ancho, alto = p["dims"]
        salida.append({
            "content": p["content"] or "Productos para mascotas",
            "amount": 1,
            "type": "box",
            "dimensions": {"length": largo, "width": ancho, "height": alto},
            "weight": max(0.1, p["weight"]),
            "insurance": 0,
            "declaredValue": valor,
            "weightUnit": "KG",
            "lengthUnit": "CM",
        })
    return salida


# ══════════════════════════════════════════════════════════════════════════════
# HTTP
# ══════════════════════════════════════════════════════════════════════════════


def _headers() -> dict:
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json; charset=utf-8"}


def cuerpo_json(body: dict) -> bytes:
    """El JSON que viaja a Envia, con las tildes y la eñe en UTF-8 CRUDO.

    DESCUBIERTO EN PRODUCCIÓN (16-oct-2026): con la eñe escapada como `\\u00f1`
    —que es lo que hace `json.dumps` por defecto y httpx < 0.28— Envia responde
    `{"code": 400, "message": "Internal error"}` con HTTP 200. Con la eñe tal cual
    funciona. "Pañales", "Pequeños" y "Cachorro" están en media tienda, así que
    sin esto media tienda no cotizaba.
    """
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


async def _post(path: str, body: dict, timeout: float = 40) -> dict:
    if not TOKEN:
        raise EnviaError("Envíos por transportadora no configurados (falta ENVIA_TOKEN).")
    try:
        async with httpx.AsyncClient(timeout=timeout) as cli:
            r = await cli.post(f"{API}{path}", content=cuerpo_json(body), headers=_headers())
    except httpx.HTTPError as exc:
        raise EnviaError("La transportadora no respondió. Intenta de nuevo en un momento.") from exc
    if r.status_code == 401:
        raise EnviaError("Envia rechazó el token (401): revisa ENVIA_TOKEN y ENVIA_ENV.")
    try:
        datos = r.json()
    except ValueError as exc:
        raise EnviaError(f"Respuesta no válida de Envia ({r.status_code}).") from exc
    if not isinstance(datos, dict):
        raise EnviaError(f"Respuesta inesperada de Envia ({r.status_code}).")
    # Envia tiene DOS formas de decir que algo falló: `{"meta":"error","error":{…}}`
    # y `{"code":400,"message":"Internal error","description":"…ep-…"}` — esta
    # última con HTTP 200. Las dos tienen que sonar; un error que pasa como "sin
    # tarifas" deja al cliente sin explicación y a nosotros sin pista.
    codigo = datos.get("code")
    if datos.get("meta") == "error" or r.status_code >= 400 or (
        isinstance(codigo, int) and codigo >= 400
    ):
        err = datos.get("error") or {}
        msg = (err.get("message") or err.get("description")
               or " · ".join(str(datos.get(k)) for k in ("message", "description") if datos.get(k))
               or str(datos)[:200])
        log.warning("ENVIA · %s respondió error: %s", path, msg)
        raise EnviaError(msg)
    return datos


async def _get(url: str, params: dict | None = None, timeout: float = 20) -> dict | list:
    try:
        async with httpx.AsyncClient(timeout=timeout) as cli:
            r = await cli.get(url, params=params, headers=_headers())
    except httpx.HTTPError as exc:
        raise EnviaError("Envia no respondió.") from exc
    try:
        return r.json()
    except ValueError as exc:
        raise EnviaError(f"Respuesta no válida de Envia ({r.status_code}).") from exc


# ══════════════════════════════════════════════════════════════════════════════
# Ciudad → código DANE
# ══════════════════════════════════════════════════════════════════════════════

_TTL = 7 * 86_400
_cache_locate: dict[str, tuple[float, dict | None]] = {}


def _sin_tildes(s: str) -> str:
    tabla = str.maketrans("áéíóúÁÉÍÓÚñÑüÜ", "aeiouAEIOUnNuU")
    return (s or "").translate(tabla).strip()


async def localizar(ciudad: str, departamento: str) -> dict | None:
    """Ciudad + departamento → `{"dane": "11001000", "nombre": "BOGOTA", "state": "DC"}`.

    Sin token (el endpoint es público). Se guarda una semana: los municipios no
    cambian de código. Devuelve None si Envia no la encuentra.
    """
    dep = (departamento or "").strip().upper()
    nombre = _sin_tildes(ciudad)
    if not dep or len(nombre) < 2:
        return None
    clave = f"{dep}|{nombre.lower()}"
    guardado = _cache_locate.get(clave)
    if guardado and time.monotonic() - guardado[0] < _TTL:
        return guardado[1]
    resultado: dict | None = None
    try:
        async with httpx.AsyncClient(timeout=15) as cli:
            r = await cli.post(
                f"{API}/locate", json={"city": nombre, "state": dep, "country": "CO"}
            )
        d = r.json() if r.status_code == 200 else {}
        if d.get("city") and d.get("state"):
            resultado = {
                "dane": str(d["city"]),
                "nombre": (d.get("name") or nombre).strip().title(),
                "state": str(d["state"]).upper(),
            }
    except Exception:
        log.exception("ENVIA · falló /locate para %r, %s", ciudad, dep)
        return None
    _cache_locate[clave] = (time.monotonic(), resultado)
    return resultado


async def codigo_postal(ciudad: str, dane: str, departamento: str) -> str | None:
    """Un código postal válido para la ciudad, o None.

    Las transportadoras colombianas enrutan por el DANE, pero Envia exige
    `postalCode`. Se busca en su propio catálogo de códigos filtrando por el DANE de
    5 dígitos (el `locate` por nombre devuelve homónimos: "Dosquebradas" también
    existe en Caldas y en Cauca).
    """
    try:
        async with httpx.AsyncClient(timeout=15) as cli:
            r = await cli.get(f"{GEOCODES}/locate/CO/{_sin_tildes(ciudad)}")
        datos = r.json() if r.status_code == 200 else []
    except Exception:
        return None
    if not isinstance(datos, list):
        return None
    prefijo = (dane or "")[:5]
    for bloque in datos:
        for z in bloque.get("zip_codes", []):
            if str((z.get("info") or {}).get("stat") or "") == prefijo and z.get("zip_code"):
                return str(z["zip_code"])
    # Si el catálogo de Envia no tiene la ciudad con ese DANE, se le pregunta a
    # Google por el centro del municipio: devuelve el código postal cuando lo tiene.
    try:
        from app.services.cobertura import _geocodificar

        g = await _geocodificar(f"{ciudad}, {DEPARTAMENTO_NOMBRE.get(departamento, departamento)}, Colombia")
        for comp in (g or {}).get("address_components", []):
            if "postal_code" in comp.get("types", []):
                cp = re.sub(r"\D", "", comp.get("long_name") or "")
                if len(cp) == 6:
                    return cp
    except Exception:
        log.exception("ENVIA · falló el postal por Google para %r", ciudad)
    for bloque in datos:
        if ((bloque.get("state") or {}).get("code") or {}).get("2digit") == departamento:
            for z in bloque.get("zip_codes", []):
                if z.get("zip_code"):
                    return str(z["zip_code"])
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Destino
# ══════════════════════════════════════════════════════════════════════════════


def destino_a_envia(d: dict) -> dict:
    """Del destino guardado en el pedido al bloque `destination` de Envia.

    `d` es lo que escribió el cliente, ya validado: nombre, telefono, calle, barrio,
    referencia, ciudad, dane, departamento, postal, cedula, email, lat, lng.
    """
    calle = (d.get("calle") or "").strip()
    numero = ""
    m = re.match(r"^(.*?)\s*(?:#|No\.?|N°|Nº)\s*(.+)$", calle, re.IGNORECASE)
    if m:
        calle, numero = m.group(1).strip(), m.group(2).strip()
    dest = {
        "name": (d.get("nombre") or "")[:80],
        "company": "",
        "email": (d.get("email") or "")[:120],
        "phone": re.sub(r"\D", "", d.get("telefono") or "")[:15],
        "phone_code": "CO",
        "street": calle[:100] or (d.get("calle") or "")[:100],
        "number": numero[:30],
        "district": (d.get("barrio") or "")[:80],
        "city": str(d.get("dane") or ""),
        "state": str(d.get("departamento") or "").upper(),
        "country": "CO",
        "postalCode": str(d.get("postal") or ""),
        "reference": (d.get("referencia") or "")[:120],
    }
    if d.get("cedula"):
        dest["identificationNumber"] = re.sub(r"\D", "", str(d["cedula"]))[:20]
    if d.get("lat") is not None and d.get("lng") is not None:
        dest["coordinates"] = {"latitude": str(d["lat"]), "longitude": str(d["lng"])}
    return dest


# ══════════════════════════════════════════════════════════════════════════════
# Cotizar
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class Tarifa:
    carrier: str
    carrier_nombre: str
    service: str
    service_nombre: str
    #: Lo que paga el cliente: tarifa de Envia + margen, redondeada a la centena.
    precio: int
    #: Lo que cobra Envia por la guía, tal cual.
    precio_envia: float
    dias: str
    fecha_estimada: str | None
    dias_numero: int | None
    puerta_a_puerta: bool

    def dict(self) -> dict:
        return asdict(self)


def _precio_cliente(precio_envia: float) -> int:
    con_margen = precio_envia * (1 + MARGEN_PCT / 100)
    return int(math.ceil(con_margen / 100.0) * 100)


#: Servicios que no aplican a un paquete entre ciudades: documentos y "mismo día"
#: (los "Rapi Hoy" y similares son urbanos; el sandbox los devuelve igual para
#: Dosquebradas → Bogotá, y prometerle eso a un cliente sería mentirle).
_SERVICIOS_EXCLUIDOS = ("doc", "document", "sobre", "envelope", "same_day", "sameday", "hoy")


#: CACHÉ DE TARIFAS (17-oct-2026). Envia limita las consultas por minuto: cotizando
#: la tabla para Google respondió "Too Many Requests" y "Bad Gateway". Cada
#: cotización del checkout pregunta a 4 transportadoras a la vez, y al crear el
#: pedido se vuelve a preguntar; varios clientes a la vez podían quedarse sin
#: tarifas. La misma ruta con el mismo paquete devuelve lo mismo durante 15 min.
_TTL_TARIFA = 15 * 60
_cache_tarifas: dict[str, tuple[float, dict]] = {}


async def _tarifa_de(carrier: str, destino: dict, paquetes: list[dict]) -> list[Tarifa]:
    body = {
        "origin": ORIGEN,
        "destination": destino,
        "packages": paquetes,
        "shipment": {"carrier": carrier, "type": 1},
        "settings": {"currency": "COP"},
    }
    clave = json.dumps(
        [carrier, destino.get("city"), destino.get("postalCode"), paquetes], sort_keys=True, ensure_ascii=False
    )
    guardado = _cache_tarifas.get(clave)
    if guardado and time.monotonic() - guardado[0] < _TTL_TARIFA:
        datos = guardado[1]
    else:
        datos = None
        for intento in range(2):
            try:
                datos = await _post("/ship/rate/", body, timeout=30)
                break
            except EnviaError as exc:
                saturado = any(x in str(exc) for x in ("Too Many", "Bad Gateway", "Gateway", "no respondió"))
                if intento == 0 and saturado:
                    await asyncio.sleep(1.2)
                    continue
                log.info("ENVIA · %s sin tarifa: %s", carrier, exc)
                return []
        if datos is None:
            return []
        _cache_tarifas[clave] = (time.monotonic(), datos)
        if len(_cache_tarifas) > 2000:
            for k in list(_cache_tarifas)[:500]:
                _cache_tarifas.pop(k, None)
    salida: list[Tarifa] = []
    for t in datos.get("data") or []:
        servicio = str(t.get("service") or "")
        if any(x in servicio.lower() for x in _SERVICIOS_EXCLUIDOS):
            continue
        try:
            precio_envia = float(t.get("totalPrice") or 0)
        except (TypeError, ValueError):
            continue
        if precio_envia <= 0:
            continue
        fecha = (t.get("deliveryDate") or {}) or {}
        dias_num = fecha.get("dateDifference")
        if (fecha.get("timeUnit") or "days") != "days":
            dias_num = 0
        salida.append(
            Tarifa(
                carrier=carrier,
                carrier_nombre=NOMBRES.get(carrier, carrier.title()),
                service=servicio,
                service_nombre=str(t.get("serviceDescription") or servicio),
                precio=_precio_cliente(precio_envia),
                precio_envia=precio_envia,
                dias=str(t.get("deliveryEstimate") or ""),
                fecha_estimada=fecha.get("date"),
                dias_numero=int(dias_num) if isinstance(dias_num, int | float) else None,
                puerta_a_puerta=(t.get("dropOff") in (0, "0", None)),
            )
        )
    return salida


async def cotizar(destino: dict, paquetes: list[dict], carriers: list[str] | None = None) -> list[Tarifa]:
    """Todas las tarifas disponibles, de más barata a más cara.

    Una transportadora a la vez según Envia; aquí se preguntan todas en paralelo y
    se queda, por transportadora, el servicio más barato que llegue a la puerta. Las
    que no cubren la ruta sencillamente no aparecen.
    """
    carriers = carriers or CARRIERS
    resultados = await asyncio.gather(*(_tarifa_de(c, destino, paquetes) for c in carriers))
    mejores: dict[str, Tarifa] = {}
    for lista in resultados:
        for t in lista:
            if not t.puerta_a_puerta:
                continue
            actual = mejores.get(t.carrier)
            if actual is None or t.precio < actual.precio:
                mejores[t.carrier] = t
    return sorted(mejores.values(), key=lambda t: (t.precio, t.dias_numero or 99))


async def tarifa_exacta(destino: dict, paquetes: list[dict], carrier: str, service: str) -> Tarifa | None:
    """Vuelve a pedir la tarifa de UN servicio concreto. Es lo que se usa al crear el
    pedido: lo que se cobra es lo que la transportadora dice HOY, no lo que el
    navegador mandó."""
    for t in await _tarifa_de(carrier, destino, paquetes):
        if t.service == service:
            return t
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Guía, rastreo, cancelación, recogida, sucursales
# ══════════════════════════════════════════════════════════════════════════════


async def generar_guia(
    destino: dict, paquetes: list[dict], carrier: str, service: str,
    referencia: str, comentarios: str = "",
) -> dict:
    """Genera la guía. Descuenta saldo de la cuenta de Envia.

    Devuelve el primer elemento de `data`: `trackingNumber`, `trackUrl`, `label`
    (PDF), `shipmentId`, `totalPrice`, `currentBalance`.
    """
    body = {
        "origin": ORIGEN,
        "destination": destino,
        "packages": paquetes,
        "shipment": {"carrier": carrier, "service": service, "type": 1, "orderReference": referencia[:40]},
        "settings": {
            "currency": "COP",
            "printFormat": "PDF",
            "printSize": "STOCK_4X6",
            "comments": (comentarios or f"Pedido {referencia} · Bigotes y Paticas")[:200],
        },
    }
    datos = await _post("/ship/generate/", body, timeout=90)
    lista = datos.get("data") or []
    if not lista or not lista[0].get("trackingNumber"):
        raise EnviaError("Envia no devolvió número de guía.")
    return lista[0]


async def rastrear(trackings: list[str]) -> list[dict]:
    datos = await _post("/ship/generaltrack/", {"trackingNumbers": trackings}, timeout=40)
    return datos.get("data") or []


async def cancelar_guia(carrier: str, tracking: str) -> dict:
    """Cancela y pide la devolución del saldo. Solo sirve antes de que la
    transportadora escanee la guía; después Envia responde con error."""
    datos = await _post("/ship/cancel/", {"carrier": carrier, "trackingNumber": tracking}, timeout=40)
    lista = datos.get("data")
    if isinstance(lista, list):
        return lista[0] if lista else {}
    return lista or {}


async def programar_recogida(
    carrier: str, fecha: str, desde: int, hasta: int, trackings: list[str],
    total_paquetes: int, peso_kg: float, instrucciones: str = "",
) -> dict:
    """Pide que la transportadora pase por el local. `fecha` AAAA-MM-DD, horas enteras."""
    body = {
        "origin": {**ORIGEN, "postal_code": ORIGEN["postalCode"]},
        "shipment": {
            "type": 1,
            "carrier": carrier,
            "pickup": {
                "weightUnit": "KG",
                "totalWeight": round(peso_kg, 2),
                "totalPackages": total_paquetes,
                "date": fecha,
                "timeFrom": int(desde),
                "timeTo": int(hasta),
                "carrier": carrier,
                "instructions": (instrucciones or "Samara Plaza Mall, Local 2 · Bigotes y Paticas")[:200],
                "trackingNumbers": trackings,
            },
        },
    }
    datos = await _post("/ship/pickup/", body, timeout=60)
    lista = datos.get("data")
    if isinstance(lista, list):
        return lista[0] if lista else {}
    return lista or {}


async def sucursales(carrier: str, ciudad: str = "Dosquebradas", postal: str = "661001", limite: int = 8) -> list[dict]:
    """Puntos de la transportadora donde se puede dejar el paquete. `[]` si no hay."""
    try:
        datos = await _get(
            f"{QUERIES}/branches/{carrier}/CO",
            params={"zipcode": postal, "state": "Risaralda", "locality": ciudad, "type": 1, "limitBranches": limite},
        )
    except EnviaError:
        return []
    if isinstance(datos, dict):
        datos = datos.get("data") or []
    return datos if isinstance(datos, list) else []


async def transportadoras() -> list[dict]:
    datos = await _get(f"{QUERIES}/carrier", params={"country_code": "CO"})
    return datos.get("data") if isinstance(datos, dict) else []
