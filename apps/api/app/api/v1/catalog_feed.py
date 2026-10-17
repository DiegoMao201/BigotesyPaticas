"""Feed XML de productos para Meta Catalog / Google Merchant.

URL pública: GET /v1/catalog/products.xml
Meta leerá este feed periódicamente para sincronizar el catálogo.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from io import BytesIO

from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import text

from app.deps import DBSession

router = APIRouter(prefix="/v1/catalog", tags=["catalog-feed"])

_STORE_URL = "https://bigotesypaticas.com"

# Merchant Center lee ESTE feed (no /merchant.xml de la tienda) — verificado por API
# el 25-sep-2026. Las fotos del CDN miden 230-380 px de ancho y Google exige 500:
# tenía 11 productos rechazados y 506 con aviso. Se mandan por /img-feed de la
# tienda, que las entrega a 1000x1000 (mismo arreglo que ya tenía merchant.xml).
_RE_CDN = re.compile(r"/bigotesypaticas/products/([a-z0-9][a-z0-9-]*)/main\.webp$")


def _imagen_para_google(url: str | None) -> str | None:
    """URL del CDN -> /img-feed/<slug>.jpg; si no tiene la forma esperada, tal cual."""
    if not url:
        return url
    m = _RE_CDN.search(url)
    return f"{_STORE_URL}/img-feed/{m.group(1)}.jpg" if m else url


# Mapa de categoría propia → taxonomía Google Merchant
_GOOGLE_CAT: dict[str, str] = {
    "CONCENTRADO": "Animals & Pet Supplies > Pet Supplies > Dog Supplies > Dog Food",
    "SNACK": "Animals & Pet Supplies > Pet Supplies > Dog Supplies > Dog Treats",
    "MEDICAMENTO": "Animals & Pet Supplies > Pet Supplies > Pet Health Supplies",
    "ARENA": "Animals & Pet Supplies > Pet Supplies > Cat Supplies > Cat Litter",
    "Accesorios": "Animals & Pet Supplies > Pet Supplies",
    "Aseo": "Animals & Pet Supplies > Pet Supplies > Pet Grooming Supplies",
    "Juguetes": "Animals & Pet Supplies > Pet Supplies > Dog Supplies > Dog Toys",
    "Perros": "Animals & Pet Supplies > Pet Supplies > Dog Supplies",
    "Gatos": "Animals & Pet Supplies > Pet Supplies > Cat Supplies",
    "Snacks": "Animals & Pet Supplies > Pet Supplies > Dog Supplies > Dog Treats",
}

# Mapa de categoría → tipo mascota (custom_label_1)
_PET_TYPE: dict[str, str] = {
    "CONCENTRADO": "perro-gato",
    "SNACK": "perro",
    "MEDICAMENTO": "perro-gato",
    "ARENA": "gato",
    "Accesorios": "perro-gato",
    "Aseo": "perro-gato",
    "Juguetes": "perro",
    "Snacks": "perro",
    "Perros": "perro",
    "Gatos": "gato",
}


# ─── Detalles que Google pide en la descripción ──────────────────────────────
# Merchant Center reclamó 93 productos de comida para perros: "actualiza las
# descripciones para incluir los detalles que buscan los clientes", y en todos
# señalaba lo mismo — el SABOR. La base ya tiene descripción larga, beneficios,
# detalles técnicos y recomendaciones para los 546 productos; el feed solo mandaba
# `descripcion_corta` (118 caracteres de media). Aquí se arma la descripción
# completa y se emiten los atributos estructurados que Google sabe leer.

# El ingrediente solo está cargado en 89 de 546 fichas, pero el nombre del producto
# casi siempre lo lleva ("Max Perro Mature +7 Frango Y Arroz 2 Kg").
_SABORES = [
    ("cordero y arroz", "Cordero y arroz"), ("pollo y arroz", "Pollo y arroz"),
    ("frango y arroz", "Pollo y arroz"), ("carne y arroz", "Carne y arroz"),
    ("salmon y arroz", "Salmón y arroz"), ("salmón y arroz", "Salmón y arroz"),
    ("buey y arroz", "Buey y arroz"), ("cordero", "Cordero"), ("salmon", "Salmón"),
    ("salmón", "Salmón"), ("atun", "Atún"), ("atún", "Atún"), ("frango", "Pollo"),
    ("pollo", "Pollo"), ("pavo", "Pavo"), ("cerdo", "Cerdo"), ("buey", "Buey"),
    ("higado", "Hígado"), ("hígado", "Hígado"), ("res", "Res"), ("carne", "Carne"),
    ("pescado", "Pescado"), ("vegetal", "Vegetales"), ("buffet", "Buffet"),
    ("mix", "Mix"), ("leche", "Leche"),
]


# El sabor solo tiene sentido en lo que se come. Sin este filtro, buscar "sabor" en
# la descripción de un juguete devolvía cosas como "Silicona".
_NO_SE_COME = ("juguete", "collar", "correa", "arnes", "arnés", "pelota", "cama",
               "plato", "bebedero", "comedero", "guacal", "transportador", "cepillo",
               "shampoo", "champú", "jabon", "jabón", "arena", "pañal", "panal",
               "toalla", "rascador", "placa", "ropa", "camiseta", "bozal", "peine",
               "cortauñas", "cortaunas", "bolsa", "dispensador", "fuente", "silicona")


def _busca(clave: str, texto: str) -> bool:
    """Palabra completa. Buscando "res" como subcadena salían sabores inventados:
    estaba dentro de "fresco", "frescos" y hasta de la marca "Freshly"."""
    return re.search(rf"\b{re.escape(clave)}\b", texto) is not None


def _sabor(nombre: str, detalles: dict, descripcion: str = "", categoria: str = "") -> str | None:
    """El sabor, por orden de fiabilidad: el dato cargado, el nombre del producto, y
    por último un "sabor a ..." escrito en la descripción. Nunca se inventa: si no
    aparece en ninguno de los tres, el atributo no se emite."""
    n = (nombre or "").lower()
    if any(x in n or x in (categoria or "").lower() for x in _NO_SE_COME):
        return None
    ing = (detalles or {}).get("ingredientes_principales")
    if ing:
        return str(ing)[:100]
    for clave, etiqueta in _SABORES:
        if _busca(clave, n):
            return etiqueta
    d = (descripcion or "").lower()
    for clave, etiqueta in _SABORES:
        if _busca(clave, d):
            return etiqueta
    return None


_EDAD = {"puppy": "Cachorro", "kitten": "Cachorro", "adult": "Adulto",
         "senior": "Senior", "all": "Todas las edades"}
_TALLA = {"small": "Raza pequeña", "medium": "Raza mediana", "large": "Raza grande",
          "giant": "Raza gigante", "all": "Todas las razas"}


def _detalles_producto(p, ec: dict, categoria: str = "") -> list[tuple[str, str]]:
    """Pares (nombre, valor) para g:product_detail. Son los datos por los que la
    gente filtra en Google: sabor, presentación, edad y tamaño de raza."""
    dt = (ec.get("detalles_tecnicos") or {}) if ec else {}
    out: list[tuple[str, str]] = []
    sabor = _sabor(p["name"], dt, (ec or {}).get("descripcion") or "", categoria)
    if sabor:
        out.append(("Sabor", sabor))
    if dt.get("presentacion"):
        out.append(("Presentación", str(dt["presentacion"])[:100]))
    edad = _EDAD.get((p["life_stage"] or "").lower()) or (
        str(dt["edad_recomendada"]).capitalize() if dt.get("edad_recomendada") else None)
    if edad:
        out.append(("Edad recomendada", edad))
    talla = _TALLA.get((p["size_range"] or "").lower()) or (
        str(dt["tamano_recomendado"]).capitalize() if dt.get("tamano_recomendado") else None)
    if talla:
        out.append(("Tamaño de raza", talla))
    if dt.get("principio_activo"):
        out.append(("Principio activo", str(dt["principio_activo"])[:100]))
    return out


def _descripcion_rica(p, ec: dict, detalles: list[tuple[str, str]]) -> str:
    """La descripción larga + beneficios + ficha + para quién es. Google premia la
    descripción que responde lo que el cliente pregunta; la corta de 118 caracteres
    no respondía nada."""
    partes: list[str] = []
    larga = (ec or {}).get("descripcion") or p["description"] or p["name"]
    if larga:
        partes.append(str(larga).strip())
    if detalles:
        partes.append(" · ".join(f"{k}: {v}" for k, v in detalles))
    ben = [str(b).lstrip("✓ ").strip().rstrip(".") for b in ((ec or {}).get("beneficios") or [])][:6]
    ben = [b for b in ben if b]
    if ben:
        partes.append("Beneficios: " + "; ".join(ben) + ".")
    rec = [str(r).strip() for r in ((ec or {}).get("recomendado_para") or [])][:6]
    if rec:
        partes.append("Recomendado para: " + ", ".join(rec) + ".")
    uso = (ec or {}).get("modo_de_uso")
    if uso:
        partes.append("Modo de uso: " + str(uso).strip())
    return "\n\n".join(x for x in partes if x)[:5000]


# Google rechaza los títulos TODO EN MAYÚSCULAS y los que traen basura al final
# (un ";" suelto le costó la aprobación a un juguete en Discovery).
def _titulo_limpio(nombre: str) -> str:
    t = (nombre or "").strip().rstrip(";:,.- ").strip()
    letras = [c for c in t if c.isalpha()]
    if letras and sum(1 for c in letras if c.isupper()) / len(letras) > 0.7:
        t = " ".join(w if (w.isdigit() or len(w) <= 2) else w.capitalize() for w in t.split())
    return t[:150]


_UNIDADES = re.compile(r"(\d+[.,]?\d*)\s*(kg|kilo|kilos|g|gr|grs|gramos|ml|l|lt|litro|litros|lb)\b", re.I)
_NORMALIZA_UNIDAD = {"kilo": "kg", "kilos": "kg", "gr": "g", "grs": "g", "gramos": "g",
                     "lt": "l", "litro": "l", "litros": "l", "lb": "lb"}


# A kg o a litros siempre: la medida y su base tienen que ser de la misma magnitud
# o Google rechaza el atributo, y en kg el precio es comparable entre presentaciones.
_A_KG = {"kg": 1.0, "g": 0.001, "lb": 0.453592}
_A_L = {"l": 1.0, "ml": 0.001}


def _unidad_de_venta(texto: str) -> tuple[str, str] | None:
    """Contenido normalizado a kg o a l, para g:unit_pricing_measure. Con esto Google
    muestra el precio por kilo y el producto se puede comparar con la competencia."""
    m = _UNIDADES.search(texto or "")
    if not m:
        return None
    uni = _NORMALIZA_UNIDAD.get(m.group(2).lower(), m.group(2).lower())
    try:
        f = float(m.group(1).replace(",", "."))
    except ValueError:
        return None
    if f <= 0:
        return None
    if uni in _A_KG:
        kg = f * _A_KG[uni]
        return (f"{round(kg, 3):g}", "kg") if 0 < kg <= 200 else None
    if uni in _A_L:
        lt = f * _A_L[uni]
        return (f"{round(lt, 3):g}", "l") if 0 < lt <= 200 else None
    return None


@router.get("/products.xml", include_in_schema=False)
async def products_feed_xml(db: DBSession) -> Response:
    """Feed RSS XML compatible con Meta Catalog y Google Merchant Center."""
    rows = await db.execute(
        text("""
        SELECT
            p.id::text, p.sku, p.name,
            COALESCE(p.enriched_content->>'descripcion_corta', p.description, p.name) AS description,
            p.enriched_content,
            p.attributes,
            p.life_stage,
            p.size_range,
            p.price,
            p.compare_at_price,
            p.primary_image_url,
            p.image_url_transparent,
            p.slug,
            b.name AS brand_name,
            c.name AS category_name,
            COALESCE(i.qty, 0) AS stock_qty
        FROM catalog.products p
        LEFT JOIN catalog.brands b ON b.id = p.brand_id
        LEFT JOIN catalog.categories c ON c.id = p.category_id
        LEFT JOIN (
            SELECT product_id, SUM(quantity) AS qty
            FROM inventory.stock
            GROUP BY product_id
        ) i ON i.product_id = p.id
        WHERE p.is_active = true
          AND p.is_published = true
          AND p.primary_image_url IS NOT NULL
        ORDER BY p.created_at DESC
        LIMIT 2000
    """)
    )
    products = rows.mappings().fetchall()

    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:g", "http://base.google.com/ns/1.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Bigotes y Paticas — Catálogo"
    ET.SubElement(channel, "link").text = _STORE_URL
    ET.SubElement(
        channel, "description"
    ).text = "Catálogo de productos para mascotas en Pereira y Dosquebradas"

    for p in products:
        stock = int(p["stock_qty"] or 0)
        price = float(p["price"] or 0)
        cat_name = p["category_name"] or ""
        brand = (p["brand_name"] or "Bigotes y Paticas")[:70]
        if price <= 0:
            continue

        item = ET.SubElement(channel, "item")

        ec = p["enriched_content"] or {}
        detalles = _detalles_producto(p, ec, p["category_name"] or "")

        ET.SubElement(item, "g:id").text = str(p["sku"] or p["id"])
        ET.SubElement(item, "g:title").text = _titulo_limpio(p["name"])
        ET.SubElement(item, "g:description").text = _descripcion_rica(p, ec, detalles)
        ET.SubElement(item, "g:link").text = f"{_STORE_URL}/producto/{p['slug']}"

        # Imagen principal: la foto a 1000x1000 por /img-feed (la transparente sale con
        # fondo negro o blanco segun la superficie de Google); la transparente va de adicional.
        main_img = _imagen_para_google(p["primary_image_url"]) or p["image_url_transparent"]
        extra_img = (
            p["image_url_transparent"]
            if p["image_url_transparent"] and p["image_url_transparent"] != p["primary_image_url"]
            else None
        )
        ET.SubElement(item, "g:image_link").text = main_img
        if extra_img:
            ET.SubElement(item, "g:additional_image_link").text = extra_img

        ET.SubElement(item, "g:availability").text = "in stock" if stock > 0 else "out of stock"
        ET.SubElement(item, "g:condition").text = "new"
        # Formato requerido por Google: "XXXXX.XX COP" con 2 decimales.
        # En oferta: price = precio de antes y sale_price = el que se cobra (antes se
        # mandaba el de oferta como precio normal y Google no mostraba el descuento).
        antes = float(p["compare_at_price"] or 0)
        if antes > price:
            ET.SubElement(item, "g:price").text = f"{antes:.2f} COP"
            ET.SubElement(item, "g:sale_price").text = f"{price:.2f} COP"
        else:
            ET.SubElement(item, "g:price").text = f"{price:.2f} COP"
        ET.SubElement(item, "g:brand").text = brand

        # Código de barras: recuperado de los XML de factura de los proveedores
        # (10-oct-2026). Con GTIN, Google empareja el producto con su catálogo global
        # y lo muestra en comparadores; sin él hay que declarar identifier_exists=no.
        gtin = ((p["attributes"] or {}).get("gtin") or "").strip()
        if gtin:
            ET.SubElement(item, "g:gtin").text = gtin
        else:
            ET.SubElement(item, "g:identifier_exists").text = "no"

        # Categoría Google específica por tipo de producto
        google_cat = _GOOGLE_CAT.get(cat_name, "Animals & Pet Supplies > Pet Supplies")
        ET.SubElement(item, "g:google_product_category").text = google_cat
        if cat_name:
            ET.SubElement(item, "g:product_type").text = cat_name

        # ENVÍO (17-oct-2026). Antes cada producto declaraba "Colombia: gratis desde
        # $30.000, si no $5.000", y lo que declara el producto PISA la configuración
        # de la cuenta: le decía a Google que entregábamos gratis en todo el país.
        # Ahora el envío vive en la configuración de envío de Merchant Center (dos
        # servicios: domicilio local y envío nacional por transportadora, tabla
        # por peso), y aquí va el PESO de envío que esa tabla necesita. El peso
        # sale de attributes.peso_kg con el 10 % de empaque, como lo empaca Envia.
        try:
            peso = float((p["attributes"] or {}).get("peso_kg") or 0)
        except (TypeError, ValueError):
            peso = 0.0
        if peso > 0:
            ET.SubElement(item, "g:shipping_weight").text = f"{max(0.3, round(peso * 1.1, 2))} kg"

        # Lo que Merchant Center pedía: los detalles por los que la gente filtra.
        # Van como atributos, no solo dentro del texto, para que Google los entienda.
        for nombre_attr, valor_attr in detalles:
            det = ET.SubElement(item, "g:product_detail")
            ET.SubElement(det, "g:section_name").text = "Características"
            ET.SubElement(det, "g:attribute_name").text = nombre_attr
            ET.SubElement(det, "g:attribute_value").text = valor_attr

        # Los beneficios son los bullets que Google muestra en la ficha del producto.
        for beneficio in [str(b).lstrip("✓ ").strip() for b in (ec.get("beneficios") or [])][:6]:
            if beneficio:
                ET.SubElement(item, "g:product_highlight").text = beneficio[:150]

        # Precio por kilo/litro: deja el producto comparable con el de la competencia.
        unidad = _unidad_de_venta(
            (ec.get("detalles_tecnicos") or {}).get("presentacion") or p["name"]
        )
        if unidad:
            ET.SubElement(item, "g:unit_pricing_measure").text = f"{unidad[0]}{unidad[1]}"
            ET.SubElement(item, "g:unit_pricing_base_measure").text = f"1{unidad[1]}"

        # Custom labels para segmentación en Google Ads
        ET.SubElement(item, "g:custom_label_0").text = cat_name.lower() if cat_name else "otro"
        ET.SubElement(item, "g:custom_label_1").text = _PET_TYPE.get(cat_name, "perro-gato")
        ET.SubElement(item, "g:custom_label_2").text = brand.lower()
        # Segmento de precio para Smart Shopping
        if price < 20000:
            price_band = "menos-20k"
        elif price < 50000:
            price_band = "20k-50k"
        elif price < 100000:
            price_band = "50k-100k"
        else:
            price_band = "mas-100k"
        ET.SubElement(item, "g:custom_label_3").text = price_band
        ET.SubElement(item, "g:custom_label_4").text = "in-stock" if stock > 0 else "out-of-stock"

    buf = BytesIO()
    ET.ElementTree(rss).write(buf, encoding="UTF-8", xml_declaration=True)

    return Response(
        content=buf.getvalue(),
        media_type="application/xml",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Type": "application/xml; charset=utf-8",
        },
    )
