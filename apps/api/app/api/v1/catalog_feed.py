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
_CDN_BASE  = "https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com"


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
        stock = int(p["stock_qty"] or 0)
        price = float(p["price"] or 0)
        if price <= 0:
            continue

        item = ET.SubElement(channel, "item")

        ET.SubElement(item, "g:id").text        = str(p["sku"] or p["id"])
        ET.SubElement(item, "g:title").text     = (p["name"] or "")[:150]
        ET.SubElement(item, "g:description").text = (p["description"] or p["name"] or "")[:5000]
        ET.SubElement(item, "g:link").text      = f"{_STORE_URL}/producto/{p['slug']}"
        ET.SubElement(item, "g:image_link").text = (
            p["image_url_transparent"] or p["primary_image_url"]
        )
        ET.SubElement(item, "g:availability").text  = "in stock" if stock > 0 else "out of stock"
        ET.SubElement(item, "g:condition").text     = "new"
        ET.SubElement(item, "g:price").text         = f"{int(price)} COP"
        ET.SubElement(item, "g:brand").text         = (p["brand_name"] or "Bigotes y Paticas")
        ET.SubElement(item, "g:identifier_exists").text = "no"
        ET.SubElement(item, "g:google_product_category").text = (
            "Animals & Pet Supplies > Pet Supplies"
        )
        if p["category_name"]:
            ET.SubElement(item, "g:product_type").text = p["category_name"]

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
