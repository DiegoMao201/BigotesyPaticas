"""Feed XML de productos para Meta Catalog / Google Merchant.

URL pública: GET /v1/catalog/products.xml
Meta leerá este feed periódicamente para sincronizar el catálogo.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from io import BytesIO

from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import text

from app.deps import DBSession

router = APIRouter(prefix="/v1/catalog", tags=["catalog-feed"])

_STORE_URL = "https://bigotesypaticas.com"

# Mapa de categoría propia → taxonomía Google Merchant
_GOOGLE_CAT: dict[str, str] = {
    "CONCENTRADO":  "Animals & Pet Supplies > Pet Supplies > Dog Supplies > Dog Food",
    "SNACK":        "Animals & Pet Supplies > Pet Supplies > Dog Supplies > Dog Treats",
    "MEDICAMENTO":  "Animals & Pet Supplies > Pet Supplies > Pet Health Supplies",
    "ARENA":        "Animals & Pet Supplies > Pet Supplies > Cat Supplies > Cat Litter",
    "Accesorios":   "Animals & Pet Supplies > Pet Supplies",
    "Aseo":         "Animals & Pet Supplies > Pet Supplies > Pet Grooming Supplies",
    "Juguetes":     "Animals & Pet Supplies > Pet Supplies > Dog Supplies > Dog Toys",
    "Perros":       "Animals & Pet Supplies > Pet Supplies > Dog Supplies",
    "Gatos":        "Animals & Pet Supplies > Pet Supplies > Cat Supplies",
    "Snacks":       "Animals & Pet Supplies > Pet Supplies > Dog Supplies > Dog Treats",
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


@router.get("/products.xml", include_in_schema=False)
async def products_feed_xml(db: DBSession) -> Response:
    """Feed RSS XML compatible con Meta Catalog y Google Merchant Center."""
    rows = await db.execute(text("""
        SELECT
            p.id::text, p.sku, p.name,
            COALESCE(p.enriched_content->>'descripcion_corta', p.description, p.name) AS description,
            p.price,
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
    """))
    products = rows.mappings().fetchall()

    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:g", "http://base.google.com/ns/1.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Bigotes y Paticas — Catálogo"
    ET.SubElement(channel, "link").text = _STORE_URL
    ET.SubElement(channel, "description").text = (
        "Catálogo de productos para mascotas en Pereira y Dosquebradas"
    )

    for p in products:
        stock    = int(p["stock_qty"] or 0)
        price    = float(p["price"] or 0)
        cat_name = p["category_name"] or ""
        brand    = (p["brand_name"] or "Bigotes y Paticas")[:70]
        if price <= 0:
            continue

        item = ET.SubElement(channel, "item")

        ET.SubElement(item, "g:id").text          = str(p["sku"] or p["id"])
        ET.SubElement(item, "g:title").text        = (p["name"] or "")[:150]
        ET.SubElement(item, "g:description").text  = (p["description"] or p["name"] or "")[:5000]
        ET.SubElement(item, "g:link").text         = f"{_STORE_URL}/producto/{p['slug']}"

        # Imagen principal (transparente preferida) + imagen adicional si existe la otra
        main_img  = p["image_url_transparent"] or p["primary_image_url"]
        extra_img = p["primary_image_url"] if p["image_url_transparent"] and p["primary_image_url"] != p["image_url_transparent"] else None
        ET.SubElement(item, "g:image_link").text   = main_img
        if extra_img:
            ET.SubElement(item, "g:additional_image_link").text = extra_img

        ET.SubElement(item, "g:availability").text = "in stock" if stock > 0 else "out of stock"
        ET.SubElement(item, "g:condition").text    = "new"
        # Formato requerido por Google: "XXXXX.XX COP" con 2 decimales
        ET.SubElement(item, "g:price").text        = f"{price:.2f} COP"
        ET.SubElement(item, "g:brand").text        = brand
        ET.SubElement(item, "g:identifier_exists").text = "no"

        # Categoría Google específica por tipo de producto
        google_cat = _GOOGLE_CAT.get(cat_name, "Animals & Pet Supplies > Pet Supplies")
        ET.SubElement(item, "g:google_product_category").text = google_cat
        if cat_name:
            ET.SubElement(item, "g:product_type").text = cat_name

        # Envío Colombia — gratis desde $30.000, sino $5.000
        ship = ET.SubElement(item, "g:shipping")
        ET.SubElement(ship, "g:country").text  = "CO"
        ET.SubElement(ship, "g:service").text  = "Domicilio Pereira y Dosquebradas"
        ship_price = "0.00 COP" if price >= 30000 else "5000.00 COP"
        ET.SubElement(ship, "g:price").text    = ship_price

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
