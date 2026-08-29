#!/usr/bin/env python3
"""
Clasificación masiva de productos con Gemini Flash — Bigotes y Paticas.

Rellena TODOS los campos de filtros y categorías a partir del nombre del producto.
El nombre NO se modifica.

Campos que actualiza:
  - category_id      → nueva taxonomía (Concentrado/Snacks/Higiene/Medicamentos/Accesorios/Juguetes)
  - pet_type         → dog | cat | both
  - life_stage       → puppy | adult | senior | all
  - size_range       → mini | small | medium | large | giant | all
  - brand_normalized → royal_canin | hills | pro_plan | ...
  - health_concerns  → [digestive, urinary, renal, ...]
  - short_description→ frase corta en español (80-120 chars)
  - tags             → array de palabras clave en español

Uso:
  python scripts/classify_products.py --dry-run --limit=10
  python scripts/classify_products.py --limit=50
  python scripts/classify_products.py               # todos los productos
  python scripts/classify_products.py --resume      # solo los sin short_description

Env requeridas:
  DATABASE_URL=postgresql+asyncpg://...
  OPENROUTER_API_KEY=sk-or-v1-...
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time

import asyncpg
import httpx

# ─── Config ─────────────────────────────────────────────────────────────────
DB_URL = (
    os.environ.get("DATABASE_URL", "")
    .replace("postgresql+psycopg://", "postgresql://")
    .replace("postgresql+asyncpg://", "postgresql://")
)
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.5-flash-lite"
CONCURRENCY = 8
BATCH_SIZE = 20  # productos por llamada a la API

# ─── Taxonomía de categorías ─────────────────────────────────────────────────
# slug → nombre visible en español
CATEGORIES = {
    "concentrado": "Concentrado",
    "snacks": "Snacks",
    "higiene": "Higiene",
    "medicamentos": "Medicamentos",
    "accesorios": "Accesorios",
    "juguetes": "Juguetes",
}

VALID_PET_TYPES = {"dog", "cat", "both"}
VALID_LIFE_STAGES = {"puppy", "adult", "senior", "all"}
VALID_SIZE_RANGES = {"mini", "small", "medium", "large", "giant", "all"}
VALID_HEALTH_CONCERNS = {
    "digestive",
    "urinary",
    "hypoallergenic",
    "renal",
    "hepatic",
    "cardiac",
    "joint",
    "weight_management",
    "skin_sensitive",
    "grain_free",
    "dental",
    "recovery",
    "immune",
    "anxiety",
}

SYSTEM_PROMPT = f"""Eres un experto en productos para mascotas en Colombia.
Recibirás una lista de productos (nombre + SKU) y debes clasificar CADA UNO.
El nombre NO se traduce ni se modifica — solo clasifica.

CATEGORÍAS DISPONIBLES (elige exactamente uno de estos slugs):
- concentrado   → alimento principal: croquetas, kibble, alimento húmedo, latas, comida
- snacks        → premios, golosinas, snacks, huesos masticables, galletas
- higiene       → shampoo, acondicionador, cepillo, toallitas, arena, desodorante, limpieza dental, pañales, antipulgas tópico
- medicamentos  → tabletas, inyecciones, vitaminas, suplementos, antiparasitarios orales, vacunas, antibióticos, ml, mg
- accesorios    → collares, correas, arnés, ropa, camas, transportadoras, comederos, bebederos, jaulas
- juguetes      → pelotas, juguetes, rascadores, cañas, lasers, túneles

REGLAS:
1. pet_type: "dog"=perros, "cat"=gatos, "both"=ambos/general
2. life_stage: "puppy"=cachorros/junior/kitten, "adult"=adultos, "senior"=mayores 7+años, "all"=todas las edades
3. size_range: "mini"/<5kg, "small"/5-10kg, "medium"/10-25kg, "large"/25-45kg, "giant"/>45kg, "all"=todos los tamaños
4. brand_normalized: nombre de marca en snake_case minúscula (royal_canin, hills, pro_plan, etc). "sin_marca" si es genérico.
5. health_concerns: array vacío [] si no aplica. Solo de: {sorted(VALID_HEALTH_CONCERNS)}
6. short_description: 1 frase en español colombiano, 70-110 caracteres, que describe el producto. No inventar datos técnicos.
7. tags: 4-8 palabras clave en español (sin tildes) para búsquedas internas.

DEVUELVE SOLO un JSON array con un objeto por producto, en el MISMO ORDEN que la entrada:
[
  {{
    "sku": "SKU del producto",
    "category": "slug de categoría",
    "pet_type": "dog|cat|both",
    "life_stage": "puppy|adult|senior|all",
    "size_range": "mini|small|medium|large|giant|all",
    "brand_normalized": "marca_en_snake_case",
    "health_concerns": [],
    "short_description": "Descripción corta en español...",
    "tags": ["tag1", "tag2", "tag3"]
  }}
]
Sin markdown. Solo el array JSON."""


def clean_brand(brand: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", brand.lower().strip()).strip("_")[:100]


async def classify_batch(
    client: httpx.AsyncClient,
    products: list[dict],
) -> list[dict] | None:
    lines = "\n".join(
        f"- SKU:{p['sku']} | {p['name']} | Cat.actual: {p.get('category_name') or 'ninguna'}"
        for p in products
    )
    user_msg = f"Clasifica estos {len(products)} productos:\n\n{lines}"

    for attempt in range(3):
        try:
            resp = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://bigotesypaticas.com",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.1,
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            results = json.loads(content)
            if isinstance(results, list):
                return results
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(2**attempt)
            else:
                print(f"  ❌ Error batch: {e}", file=sys.stderr)
    return None


def validate_one(item: dict, category_map: dict[str, str]) -> dict:
    cat_slug = item.get("category", "")
    if cat_slug not in category_map:
        cat_slug = "accesorios"

    pet_type = item.get("pet_type", "both")
    if pet_type not in VALID_PET_TYPES:
        pet_type = "both"

    life_stage = item.get("life_stage", "all")
    if life_stage not in VALID_LIFE_STAGES:
        life_stage = "all"

    size_range = item.get("size_range", "all")
    if size_range not in VALID_SIZE_RANGES:
        size_range = "all"

    concerns = item.get("health_concerns") or []
    if isinstance(concerns, list):
        concerns = [c for c in concerns if c in VALID_HEALTH_CONCERNS]
    else:
        concerns = []

    brand = item.get("brand_normalized") or ""
    brand = clean_brand(brand) if brand else "sin_marca"

    short_desc = (item.get("short_description") or "").strip()[:500]

    tags = item.get("tags") or []
    tags = [str(t).lower()[:50] for t in tags[:10] if t] if isinstance(tags, list) else []

    return {
        "category_slug": cat_slug,
        "category_id": category_map[cat_slug],
        "pet_type": pet_type,
        "life_stage": life_stage,
        "size_range": size_range,
        "brand_normalized": brand,
        "health_concerns": concerns,
        "short_description": short_desc,
        "tags": tags,
    }


async def ensure_categories(conn: asyncpg.Connection) -> dict[str, str]:
    """Crea/normaliza categorías y retorna {slug_lowercase: id}.

    Busca case-insensitive para manejar slugs existentes como 'CONCENTRADO'
    o 'MEDICAMENTO' y reutilizarlos en vez de crear duplicados.
    """
    cat_map: dict[str, str] = {}
    for slug, name in CATEGORIES.items():
        # Buscar case-insensitive por slug o por nombre
        row = await conn.fetchrow(
            """SELECT id, slug, name FROM catalog.categories
               WHERE LOWER(slug) = $1 OR LOWER(name) = $2""",
            slug.lower(),
            name.lower(),
        )
        if row:
            cat_id = str(row["id"])
            cat_map[slug] = cat_id
            # Normalizar slug/nombre si están en mayúsculas o mal escritos
            if row["slug"] != slug or row["name"] != name:
                await conn.execute(
                    "UPDATE catalog.categories SET slug=$1, name=$2 WHERE id=$3",
                    slug,
                    name,
                    row["id"],
                )
                print(
                    f"  🔄 Categoría normalizada: {row['name']} → {name} (slug: {row['slug']} → {slug})"
                )
            else:
                print(f"  ✓  Categoría existente: {name}")
        else:
            new_id = await conn.fetchval(
                """INSERT INTO catalog.categories (name, slug, is_active, sort_order)
                   VALUES ($1, $2, true, 0)
                   RETURNING id""",
                name,
                slug,
            )
            cat_map[slug] = str(new_id)
            print(f"  ✅ Categoría creada: {name} ({slug})")
    return cat_map


async def run(args: argparse.Namespace) -> None:
    if not DB_URL:
        print("ERROR: DATABASE_URL no configurada", file=sys.stderr)
        sys.exit(1)
    if not OPENROUTER_KEY and not args.dry_run:
        print("ERROR: OPENROUTER_API_KEY no configurada", file=sys.stderr)
        sys.exit(1)

    conn = await asyncpg.connect(DB_URL)

    try:
        print("🔧 Verificando categorías...")
        category_map = await ensure_categories(conn)
        print(f"   Categorías disponibles: {list(category_map.keys())}\n")

        where = "p.is_active = true"
        if args.resume:
            where += " AND (p.short_description IS NULL OR p.short_description = '')"

        query = f"""
            SELECT p.id::text, p.sku, p.name,
                   cat.name AS category_name,
                   cat.slug AS category_slug
            FROM catalog.products p
            LEFT JOIN catalog.categories cat ON cat.id = p.category_id
            WHERE {where}
            ORDER BY p.name
            {'LIMIT ' + str(args.limit) if args.limit else ''}
        """
        rows = await conn.fetch(query)
        total = len(rows)
        print(f"📦 Productos a clasificar: {total}")

        if total == 0:
            print("Nada que procesar.")
            return

        if not args.dry_run and not args.yes:
            try:
                confirm = input(f"\n¿Procesar {total} productos? (s/N): ")
            except EOFError:
                confirm = "s"
            if confirm.lower() not in ("s", "si", "sí", "y", "yes"):
                print("Cancelado.")
                return

        products = [dict(r) for r in rows]
        batches = [products[i : i + BATCH_SIZE] for i in range(0, len(products), BATCH_SIZE)]

        stats = {"ok": 0, "fail": 0, "tok": 0, "t0": time.time()}
        sem = asyncio.Semaphore(CONCURRENCY // BATCH_SIZE + 1)

        async def process_batch(batch: list[dict], batch_idx: int) -> None:
            async with sem:
                skus = [p["sku"] for p in batch]
                print(
                    f"  Lote {batch_idx+1}/{len(batches)} ({len(batch)} prods) SKU {skus[0]}..{skus[-1]}",
                    end="",
                    flush=True,
                )

                async with httpx.AsyncClient() as client:
                    results = await classify_batch(client, batch)

                if results is None or len(results) != len(batch):
                    stats["fail"] += len(batch)
                    print(f"  ❌ Falló (got {len(results) if results else 0})")
                    return

                # Mapear resultados por SKU
                result_map = {r.get("sku"): r for r in results}

                for product in batch:
                    ai_result = result_map.get(product["sku"])
                    if not ai_result:
                        stats["fail"] += 1
                        continue

                    validated = validate_one(ai_result, category_map)

                    if args.dry_run:
                        if batch_idx == 0:
                            print(
                                f"\n    {product['name'][:45]:45} → {validated['category_slug']:12} | {validated['pet_type']:4} | {validated['life_stage']:6} | {validated['brand_normalized'][:20]}"
                            )
                            print(f"      desc: {validated['short_description'][:70]}")
                    else:
                        await conn.execute(
                            """UPDATE catalog.products SET
                                category_id      = $1::uuid,
                                pet_type         = $2,
                                life_stage       = $3,
                                size_range       = $4,
                                brand_normalized = $5,
                                health_concerns  = $6::text[],
                                short_description= $7,
                                tags             = $8::jsonb
                               WHERE id = $9::uuid""",
                            validated["category_id"],
                            validated["pet_type"],
                            validated["life_stage"],
                            validated["size_range"],
                            validated["brand_normalized"],
                            validated["health_concerns"],
                            validated["short_description"],
                            json.dumps(validated["tags"]),
                            product["id"],
                        )
                        stats["ok"] += 1

                if not args.dry_run:
                    print(f"  ✓ ({stats['ok']} ok / {stats['fail']} err)")
                elif batch_idx == 0:
                    print("  ✓ DRY-RUN preview mostrado")
                else:
                    print("  ✓ DRY")

        tasks = [process_batch(b, i) for i, b in enumerate(batches)]
        await asyncio.gather(*tasks)

        elapsed = time.time() - stats["t0"]
        print("\n" + "═" * 55)
        print(f"  ✅ Completado en {elapsed:.0f}s")
        if not args.dry_run:
            print(f"  Actualizados: {stats['ok']:,} / {total:,}")
            print(f"  Fallidos:     {stats['fail']:,}")
        print("═" * 55)

        if not args.dry_run and stats["ok"] > 0:
            # Verificar distribución de categorías resultante
            cat_dist = await conn.fetch(
                """SELECT cat.name, COUNT(*) as n
                   FROM catalog.products p
                   JOIN catalog.categories cat ON cat.id = p.category_id
                   WHERE p.is_active = true
                   GROUP BY cat.name ORDER BY n DESC"""
            )
            print("\n📊 Distribución final por categoría:")
            for row in cat_dist:
                print(f"   {row['n']:4d}  {row['name']}")

    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Clasificación masiva de productos con IA")
    parser.add_argument("--dry-run", action="store_true", help="Muestra resultado sin tocar DB")
    parser.add_argument(
        "--resume", action="store_true", help="Solo productos sin short_description"
    )
    parser.add_argument("--limit", type=int, default=None, help="Máximo de productos a procesar")
    parser.add_argument("--yes", "-y", action="store_true", help="Confirmar sin prompt")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
