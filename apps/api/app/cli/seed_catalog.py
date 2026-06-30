"""Seed de catálogo demo: brands, categories y productos públicos para validar
el storefront end-to-end. Idempotente.

    python -m app.cli.seed_catalog
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.catalog import Brand, Category, Product

CDN = "https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas"

BRANDS = [
    {"name": "Royal Canin", "slug": "royal-canin"},
    {"name": "Pro Plan", "slug": "pro-plan"},
    {"name": "Hill's Science Diet", "slug": "hills"},
    {"name": "Bigotes y Paticas", "slug": "bp"},
]

CATEGORIES = [
    {
        "name": "Perros",
        "slug": "perros",
        "sort_order": 1,
        "description": "Alimento, accesorios y cuidado para perros.",
    },
    {
        "name": "Gatos",
        "slug": "gatos",
        "sort_order": 2,
        "description": "Alimento, accesorios y cuidado para gatos.",
    },
    {
        "name": "Accesorios",
        "slug": "accesorios",
        "sort_order": 3,
        "description": "Correas, collares, juguetes y más.",
    },
    {
        "name": "Snacks",
        "slug": "snacks",
        "sort_order": 4,
        "description": "Premios y golosinas saludables.",
    },
]

PRODUCTS = [
    # Perros
    {
        "sku": "RC-MA-2KG",
        "slug": "royal-canin-mini-adulto-2kg",
        "name": "Royal Canin Mini Adulto 2kg",
        "short_description": "Alimento balanceado para perros adultos de razas pequeñas.",
        "description": "Royal Canin Mini Adulto está formulado para razas pequeñas (1-10kg) "
        "mayores de 10 meses. Apoya la salud digestiva y la vitalidad.",
        "brand_slug": "royal-canin",
        "category_slug": "perros",
        "price": Decimal("89000"),
        "compare_at_price": Decimal("99000"),
        "cost": Decimal("65000"),
        "is_featured": True,
        "tags": ["perro", "adulto", "raza-pequena", "premium"],
    },
    {
        "sku": "PP-AD-7KG",
        "slug": "pro-plan-adulto-7kg",
        "name": "Pro Plan Adulto Razas Medianas 7kg",
        "short_description": "Pro Plan con OptiBalance para perros adultos.",
        "description": "Nutrición avanzada con probióticos para perros adultos de razas medianas.",
        "brand_slug": "pro-plan",
        "category_slug": "perros",
        "price": Decimal("215000"),
        "cost": Decimal("160000"),
        "is_featured": True,
        "tags": ["perro", "adulto", "raza-mediana"],
    },
    # Gatos
    {
        "sku": "HSD-GAT-1.5KG",
        "slug": "hills-gato-adulto-1-5kg",
        "name": "Hill's Science Diet Gato Adulto 1.5kg",
        "short_description": "Nutrición precisa para gatos adultos.",
        "description": "Fórmula con antioxidantes clínicamente probados. Ideal para gatos de 1 a 6 años.",
        "brand_slug": "hills",
        "category_slug": "gatos",
        "price": Decimal("78000"),
        "cost": Decimal("58000"),
        "is_featured": True,
        "tags": ["gato", "adulto"],
    },
    {
        "sku": "RC-INDOOR",
        "slug": "royal-canin-indoor-cat-1-5kg",
        "name": "Royal Canin Indoor Cat 1.5kg",
        "short_description": "Para gatos que viven dentro de casa.",
        "description": "Controla la formación de bolas de pelo y reduce el olor de las heces.",
        "brand_slug": "royal-canin",
        "category_slug": "gatos",
        "price": Decimal("82000"),
        "cost": Decimal("60000"),
        "tags": ["gato", "indoor"],
    },
    # Accesorios
    {
        "sku": "BP-COL-001",
        "slug": "collar-cuero-premium-mediano",
        "name": "Collar de Cuero Premium Mediano",
        "short_description": "Collar artesanal en cuero genuino.",
        "description": "Hecho a mano en Colombia. Hebilla de acero inoxidable.",
        "brand_slug": "bp",
        "category_slug": "accesorios",
        "price": Decimal("45000"),
        "cost": Decimal("18000"),
        "is_featured": True,
        "tags": ["accesorio", "collar", "cuero"],
    },
    {
        "sku": "BP-COR-001",
        "slug": "correa-retractil-5m",
        "name": "Correa Retráctil 5 metros",
        "short_description": "Paseo cómodo y seguro.",
        "description": "Cinta resistente, freno con un click, mango ergonómico.",
        "brand_slug": "bp",
        "category_slug": "accesorios",
        "price": Decimal("65000"),
        "cost": Decimal("30000"),
        "tags": ["accesorio", "correa"],
    },
    # Snacks
    {
        "sku": "BP-SNK-001",
        "slug": "snack-natural-pollo-200g",
        "name": "Snack Natural de Pollo 200g",
        "short_description": "100% pollo deshidratado, sin conservantes.",
        "description": "Premio saludable rico en proteína. Sin colorantes ni saborizantes artificiales.",
        "brand_slug": "bp",
        "category_slug": "snacks",
        "price": Decimal("18000"),
        "cost": Decimal("8000"),
        "is_featured": True,
        "tags": ["snack", "natural", "pollo"],
    },
    {
        "sku": "BP-SNK-002",
        "slug": "galletas-dentales-300g",
        "name": "Galletas Dentales 300g",
        "short_description": "Cuidado dental mientras premias.",
        "description": "Limpieza mecánica de dientes y aliento fresco.",
        "brand_slug": "bp",
        "category_slug": "snacks",
        "price": Decimal("22000"),
        "cost": Decimal("9000"),
        "tags": ["snack", "dental"],
    },
]


async def seed_catalog() -> None:
    async with AsyncSessionLocal() as db:
        # Brands
        brand_map: dict[str, Brand] = {}
        for b in BRANDS:
            existing = (
                await db.execute(select(Brand).where(Brand.slug == b["slug"]))
            ).scalar_one_or_none()
            if existing is None:
                brand = Brand(
                    name=b["name"],
                    slug=b["slug"],
                    is_active=True,
                    logo_url=f"{CDN}/brands/{b['slug']}-logo.webp",
                )
                db.add(brand)
                brand_map[b["slug"]] = brand
                print(f"  + brand: {b['slug']}")
            else:
                brand_map[b["slug"]] = existing
        await db.flush()

        # Categories
        cat_map: dict[str, Category] = {}
        for c in CATEGORIES:
            existing = (
                await db.execute(select(Category).where(Category.slug == c["slug"]))
            ).scalar_one_or_none()
            if existing is None:
                cat = Category(
                    name=c["name"],
                    slug=c["slug"],
                    description=c.get("description"),
                    sort_order=c.get("sort_order", 0),
                    image_url=f"{CDN}/categories/{c['slug']}-banner.webp",
                    is_active=True,
                )
                db.add(cat)
                cat_map[c["slug"]] = cat
                print(f"  + category: {c['slug']}")
            else:
                cat_map[c["slug"]] = existing
        await db.flush()

        # Products
        for p in PRODUCTS:
            existing = (
                await db.execute(select(Product).where(Product.sku == p["sku"]))
            ).scalar_one_or_none()
            if existing is not None:
                continue
            brand = brand_map.get(p["brand_slug"])
            cat = cat_map.get(p["category_slug"])
            prod = Product(
                sku=p["sku"],
                slug=p["slug"],
                name=p["name"],
                short_description=p.get("short_description"),
                description=p.get("description"),
                brand_id=brand.id if brand else None,
                category_id=cat.id if cat else None,
                cost=p["cost"],
                price=p["price"],
                compare_at_price=p.get("compare_at_price"),
                margin_pct=Decimal("0.30"),
                is_active=True,
                is_published=True,
                is_featured=p.get("is_featured", False),
                primary_image_url=f"{CDN}/products/{p['slug']}/{p['slug']}-main.webp",
                images=[
                    f"{CDN}/products/{p['slug']}/{p['slug']}-main.webp",
                    f"{CDN}/products/{p['slug']}/{p['slug']}-gallery-01.webp",
                ],
                seo_title=f"{p['name']} | Bigotes y Paticas",
                seo_description=p.get("short_description") or p["name"],
                attributes={},
                tags=p.get("tags", []),
            )
            db.add(prod)
            print(f"  + product: {p['sku']} ({p['slug']})")

        await db.commit()
        print("Seed catálogo demo completado.")


def main() -> None:
    asyncio.run(seed_catalog())


if __name__ == "__main__":
    main()
