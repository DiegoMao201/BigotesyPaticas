#!/usr/bin/env python3
"""
Enriquecimiento de catálogo de productos con IA — Bigotes y Paticas.

Uso:
  python scripts/enrich_products_catalog.py --dry-run --limit=5   # Piloto sin tocar DB
  python scripts/enrich_products_catalog.py --limit=50            # Beta 50 productos
  python scripts/enrich_products_catalog.py --only-missing        # Full catálogo (faltantes)
  python scripts/enrich_products_catalog.py --only-missing --limit=100  # Lote específico
"""
import os
import sys
import json
import time
import asyncio
import httpx
from datetime import datetime

# ─── Configuración ──────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.5-flash"

DB_URL = os.environ.get("DATABASE_URL", "")
CONCURRENCY = 5
RETRY_MAX = 3

DRY_RUN = "--dry-run" in sys.argv
ONLY_MISSING = "--only-missing" in sys.argv
LIMIT = None
for arg in sys.argv:
    if arg.startswith("--limit="):
        LIMIT = int(arg.split("=")[1])

KNOWN_BRANDS = [
    "Hills", "Hill's", "Royal Canin", "Pro Plan", "Purina", "Eukanuba",
    "Bravecto", "Frontline", "Advocate", "Drontal", "Nutram", "Acana",
    "Orijen", "Taste of the Wild", "Diamond", "Pedigree", "Whiskas",
    "Fancy Feast", "Friskies", "Iams", "Kibbles", "Nexgard", "Seresto",
]

PROMPT_TEMPLATE = """Eres un redactor experto en e-commerce para mascotas en Colombia.

PRODUCTO:
- Nombre: {name}
- SKU: {sku}
- Categoría: {category_name}
- Precio: ${price:,.0f} COP
- Marca: {brand_hint}

REGLAS:
1. Español colombiano natural, cálido y profesional (estilo Bigotes y Paticas, Pereira/Dosquebradas).
2. Si el producto parece MEDICAMENTO o USO VETERINARIO (contiene palabras como "tableta", "ml", "mg",
   "antibiótico", "antiinflamatorio", "dosis", "ampolla", "jeringa", "antiséptico"):
   - En modo_de_uso escribe SOLO: "Consulta con tu veterinario para la dosificación correcta según el
     peso y condición de tu mascota. No automedicar."
   - En advertencias incluye: "Uso bajo supervisión veterinaria"
3. NUNCA inventes composición química, dosis o datos clínicos que no se infieran claramente del nombre.
4. Si no estás seguro de un dato técnico, escribe null en ese campo.
5. recomendado_para: sé específico (edad, tamaño, condición). Máximo 4 items.
6. beneficios: 3 bullets concisos con emoji ✓.
7. advertencias: array vacío [] para productos benignos (camas, juguetes, accesorios).

DEVUELVE SOLO JSON VÁLIDO — sin markdown, sin ```json, solo el objeto:

{{
  "descripcion_corta": "Frase de 80-120 caracteres que vende el producto",
  "descripcion": "2-3 oraciones sobre qué es y para qué sirve",
  "beneficios": [
    "✓ Beneficio concreto 1",
    "✓ Beneficio concreto 2",
    "✓ Beneficio concreto 3"
  ],
  "detalles_tecnicos": {{
    "presentacion": "ej: 3 kg, 250 ml, 30 tabletas",
    "principio_activo": null,
    "ingredientes_principales": null,
    "edad_recomendada": "cachorro / adulto / senior / todas las edades",
    "tamano_recomendado": "pequeño / mediano / grande / todas las tallas"
  }},
  "modo_de_uso": "Instrucciones seguras y generales de uso",
  "recomendado_para": ["Perros adultos", "Razas medianas"],
  "advertencias": []
}}"""


def detect_brand(name: str) -> str:
    name_lower = name.lower()
    for brand in KNOWN_BRANDS:
        if brand.lower() in name_lower:
            return brand
    return "Genérica"


def is_medication(name: str, category: str) -> bool:
    keywords = ["tableta", "tablet", " ml ", "mg ", "ampolla", "jeringa",
                "antibiótico", "antiinflamatorio", "antiparasit", "antifúng",
                "drontal", "bravecto", "advocate", "frontline", "nexgard"]
    text = (name + " " + (category or "")).lower()
    return any(k in text for k in keywords)


async def enrich_one(client: httpx.AsyncClient, product: dict) -> dict | None:
    brand = detect_brand(product["name"])
    med = is_medication(product["name"], product.get("category_name") or "")

    prompt = PROMPT_TEMPLATE.format(
        name=product["name"],
        sku=product.get("sku") or "N/A",
        category_name=product.get("category_name") or "Sin categoría",
        price=float(product.get("price") or 0),
        brand_hint=brand,
    )
    if med:
        prompt += "\n\nATENCIÓN: Este producto parece ser de uso veterinario/médico. Aplica regla 2."

    for attempt in range(RETRY_MAX):
        try:
            r = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://bigotesypaticas.com",
                    "X-Title": "BigotesyPaticas Catalog Enrichment",
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.65,
                    "max_tokens": 900,
                    "response_format": {"type": "json_object"},
                },
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Limpiar markdown si el modelo lo devuelve igual
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            parsed = json.loads(content)
            usage = data.get("usage", {})
            return {"data": parsed, "usage": usage}

        except json.JSONDecodeError as e:
            print(f"    ⚠️  JSON inválido (intento {attempt+1}): {e}")
        except httpx.HTTPStatusError as e:
            print(f"    ⚠️  HTTP {e.response.status_code} (intento {attempt+1})")
            if e.response.status_code == 429:
                await asyncio.sleep(10)
        except Exception as e:
            print(f"    ⚠️  Error (intento {attempt+1}): {e}")

        if attempt < RETRY_MAX - 1:
            await asyncio.sleep(2 ** attempt)

    return None


async def main() -> None:
    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY no configurada")
        sys.exit(1)
    if not DB_URL:
        print("❌ DATABASE_URL no configurada")
        sys.exit(1)

    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    engine = create_async_engine(DB_URL, pool_size=5)

    print("╔══════════════════════════════════════════════════════╗")
    print("║   Bigotes y Paticas — Enriquecimiento de catálogo   ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  Modo:        {'DRY-RUN (sin escritura DB)' if DRY_RUN else 'PRODUCCIÓN            '}")
    print(f"║  Solo nuevos: {ONLY_MISSING}")
    print(f"║  Límite:      {LIMIT or 'Todos'}")
    print(f"║  Modelo:      {MODEL}")
    print(f"║  Concurrencia:{CONCURRENCY}")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # Consulta productos
    query = """
        SELECT p.id, p.sku, p.name, p.price::float, c.name AS category_name
        FROM catalog.products p
        LEFT JOIN catalog.categories c ON c.id = p.category_id
        WHERE p.deleted_at IS NULL
          AND p.is_active = true
          AND p.is_published = true
    """
    if ONLY_MISSING:
        query += " AND p.enriched_content IS NULL"
    query += " ORDER BY p.is_featured DESC, p.created_at DESC"
    if LIMIT:
        query += f" LIMIT {LIMIT}"

    async with engine.begin() as conn:
        result = await conn.execute(text(query))
        products = [dict(r._mapping) for r in result]

    total = len(products)
    print(f"📦 Productos a enriquecer: {total}")
    if total == 0:
        print("✅ Nada que hacer — todos los productos ya están enriquecidos.")
        return

    if not DRY_RUN:
        try:
            confirm = input(f"\n¿Continuar con {total} productos en producción? [y/N]: ")
        except EOFError:
            confirm = "y"
        if confirm.lower() != "y":
            print("Cancelado")
            return

    print()
    stats = {"ok": 0, "fail": 0, "tok_in": 0, "tok_out": 0, "t0": time.time()}
    sem = asyncio.Semaphore(CONCURRENCY)

    async def process(p: dict, idx: int) -> None:
        async with sem:
            label = f"[{idx+1:03d}/{total}]"
            print(f"{label} {p['sku']} · {p['name'][:55]}", end="", flush=True)

            if DRY_RUN:
                # En dry-run igual llamamos a OpenRouter para validar formato
                async with httpx.AsyncClient() as cl:
                    result = await enrich_one(cl, p)
            else:
                async with httpx.AsyncClient() as cl:
                    result = await enrich_one(cl, p)

            if result is None:
                stats["fail"] += 1
                print("  ❌ FALLÓ")
                return

            stats["ok"] += 1
            stats["tok_in"] += result["usage"].get("prompt_tokens", 0)
            stats["tok_out"] += result["usage"].get("completion_tokens", 0)

            if DRY_RUN:
                # Mostrar preview del JSON generado
                d = result["data"]
                print(f"  ✓ DRY")
                print(f"        descripcion_corta: {d.get('descripcion_corta','')[:70]}")
                print(f"        beneficios[0]: {(d.get('beneficios') or [''])[0][:60]}")
                print(f"        modo_de_uso: {d.get('modo_de_uso','')[:60]}")
                print(f"        advertencias: {d.get('advertencias',[])}")
            else:
                async with engine.begin() as conn:
                    await conn.execute(
                        text("""
                            UPDATE catalog.products
                               SET enriched_content = CAST(:content AS jsonb),
                                   enriched_at      = :now,
                                   enriched_model   = :model
                             WHERE id = :id
                        """),
                        {
                            "content": json.dumps(result["data"], ensure_ascii=False),
                            "now": datetime.utcnow(),
                            "model": MODEL,
                            "id": str(p["id"]),
                        },
                    )
                print("  ✓")

    tasks = [process(p, i) for i, p in enumerate(products)]
    await asyncio.gather(*tasks)

    elapsed = time.time() - stats["t0"]
    cost_in = stats["tok_in"] * 0.075 / 1_000_000
    cost_out = stats["tok_out"] * 0.30 / 1_000_000
    total_cost = cost_in + cost_out

    print()
    print("═" * 58)
    print(f"  ✅ Completado en {elapsed:.1f}s")
    print(f"  Éxitos:        {stats['ok']:,} / {total:,}")
    print(f"  Fallidos:      {stats['fail']:,}")
    print(f"  Tokens entrada:{stats['tok_in']:,}")
    print(f"  Tokens salida: {stats['tok_out']:,}")
    print(f"  💵 Costo est.: ${total_cost:.4f} USD  (gemini-2.5-flash)")
    print("═" * 58)

    if not DRY_RUN and stats["ok"] > 0:
        # Verificación rápida
        async with engine.begin() as conn:
            r = await conn.execute(text("""
                SELECT COUNT(*) FROM catalog.products
                WHERE enriched_content IS NOT NULL
                  AND deleted_at IS NULL AND is_active = true
            """))
            enriched_total = r.scalar()
        print(f"\n  📊 Total enriquecidos en DB: {enriched_total:,}")


if __name__ == "__main__":
    asyncio.run(main())
