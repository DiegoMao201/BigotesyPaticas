"""
Tag catalog products with life_stage, size_range, pet_type, health_concerns, brand_normalized
using OpenRouter (Gemini Flash / DeepSeek) via AI.

Usage:
  python scripts/tag_products_with_ai.py --dry-run   # show 10 examples
  python scripts/tag_products_with_ai.py             # tag all untagged products
  python scripts/tag_products_with_ai.py --resume    # skip already-tagged products

Env:
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

import httpx
import asyncpg

DB_URL = os.environ.get("DATABASE_URL", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

VALID_LIFE_STAGES = {"puppy", "adult", "senior", "all"}
VALID_SIZE_RANGES = {"mini", "small", "medium", "large", "giant", "all"}
VALID_PET_TYPES = {"dog", "cat", "both", "small_pet", "fish", "bird"}
VALID_HEALTH_CONCERNS = {
    "digestive", "urinary", "hypoallergenic", "renal", "hepatic",
    "cardiac", "joint", "weight_management", "skin_sensitive",
    "grain_free", "dental", "recovery"
}

SYSTEM_PROMPT = """Eres un experto en productos para mascotas. Analiza el producto y devuelve SOLO un JSON válido con:
- life_stage: "puppy" | "adult" | "senior" | "all"
- size_range: "mini" | "small" | "medium" | "large" | "giant" | "all"
- health_concerns: array con tags relevantes de: digestive, urinary, hypoallergenic, renal, hepatic, cardiac, joint, weight_management, skin_sensitive, grain_free, dental, recovery
- pet_type: "dog" | "cat" | "both" | "small_pet" | "fish" | "bird"
- brand_normalized: identificador snake_case de la marca (ej: "hills", "royal_canin", "pro_plan")

Si no aplica un campo, usa "all" para life_stage/size_range, null para health_concerns, "both" para pet_type.
Devuelve SOLO el JSON, sin texto adicional, sin bloques de código."""


def validate_tags(data: dict) -> dict:
    cleaned = {}
    cleaned["life_stage"] = data.get("life_stage") if data.get("life_stage") in VALID_LIFE_STAGES else "all"
    cleaned["size_range"] = data.get("size_range") if data.get("size_range") in VALID_SIZE_RANGES else "all"
    cleaned["pet_type"] = data.get("pet_type") if data.get("pet_type") in VALID_PET_TYPES else "both"

    concerns = data.get("health_concerns")
    if isinstance(concerns, list):
        cleaned["health_concerns"] = [c for c in concerns if c in VALID_HEALTH_CONCERNS]
    else:
        cleaned["health_concerns"] = []

    brand = data.get("brand_normalized", "")
    if brand and isinstance(brand, str):
        cleaned["brand_normalized"] = re.sub(r"[^a-z0-9_]", "_", brand.lower().strip())[:100]
    else:
        cleaned["brand_normalized"] = None

    return cleaned


async def call_ai(client: httpx.AsyncClient, product: dict) -> dict | None:
    description = ""
    if product.get("enriched_content"):
        ec = product["enriched_content"]
        if isinstance(ec, dict):
            description = ec.get("descripcion_corta") or ec.get("description") or ""

    user_msg = f"""Nombre: {product['name']}
Marca: {product.get('brand') or 'Sin marca'}
Categoría: {product.get('category') or 'Sin categoría'}
Descripción: {description[:300] or 'Sin descripción'}"""

    try:
        resp = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
            json={
                "model": "google/gemini-flash-1.5-8b",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                "max_tokens": 200,
                "temperature": 0.1,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        # Remove markdown fences if present
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        data = json.loads(content)
        return validate_tags(data)
    except Exception as e:
        print(f"  AI error for {product['name'][:40]}: {e}", file=sys.stderr)
        return None


async def run(dry_run: bool, resume: bool) -> None:
    if not DB_URL:
        print("ERROR: DATABASE_URL not set.", file=sys.stderr)
        sys.exit(1)
    if not OPENROUTER_KEY and not dry_run:
        print("ERROR: OPENROUTER_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    conn = await asyncpg.connect(DB_URL)

    try:
        if resume:
            rows = await conn.fetch(
                """SELECT p.id, p.name, p.brand_id, b.name as brand,
                          cat.name as category, p.enriched_content
                   FROM catalog.products p
                   LEFT JOIN catalog.brands b ON b.id = p.brand_id
                   LEFT JOIN catalog.categories cat ON cat.id = p.category_id
                   WHERE p.is_published = true AND p.brand_normalized IS NULL
                   ORDER BY p.name"""
            )
        else:
            rows = await conn.fetch(
                """SELECT p.id, p.name, p.brand_id, b.name as brand,
                          cat.name as category, p.enriched_content
                   FROM catalog.products p
                   LEFT JOIN catalog.brands b ON b.id = p.brand_id
                   LEFT JOIN catalog.categories cat ON cat.id = p.category_id
                   WHERE p.is_published = true
                   ORDER BY p.name"""
            )

        print(f"Productos a procesar: {len(rows)}")

        if dry_run:
            print("\nDRY RUN — 10 ejemplos:")
            async with httpx.AsyncClient() as client:
                for r in rows[:10]:
                    product = dict(r)
                    tags = await call_ai(client, product)
                    print(f"\n  {product['name'][:50]}")
                    print(f"  → {tags}")
            return

        async with httpx.AsyncClient() as client:
            tagged = 0
            failed = 0
            for i, r in enumerate(rows):
                product = dict(r)
                tags = await call_ai(client, product)
                if tags:
                    await conn.execute(
                        """UPDATE catalog.products SET
                            life_stage = $1,
                            size_range = $2,
                            health_concerns = $3::text[],
                            pet_type = $4,
                            brand_normalized = $5
                           WHERE id = $6""",
                        tags["life_stage"],
                        tags["size_range"],
                        tags["health_concerns"] or [],
                        tags["pet_type"],
                        tags["brand_normalized"],
                        product["id"],
                    )
                    tagged += 1
                else:
                    failed += 1

                if (i + 1) % 50 == 0:
                    print(f"  Procesados: {i + 1}/{len(rows)} — tagged: {tagged} failed: {failed}")

                # Rate limiting (avoid 429)
                await asyncio.sleep(0.2)

        print(f"\n✅ Total tagged: {tagged}")
        print(f"⚠️  Failed: {failed}")

    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Only tag products without brand_normalized")
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run, resume=args.resume))


if __name__ == "__main__":
    main()
