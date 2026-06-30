#!/usr/bin/env python3
"""
Genera 40 landing pages SEO programáticas — Bigotes y Paticas.

Uso:
  python scripts/generate_seo_landings.py --dry-run
  python scripts/generate_seo_landings.py --limit=5
  python scripts/generate_seo_landings.py

Costo estimado: 40 landings x ~2500 tokens = ~$0.04 USD con Gemini 2.5 Flash
"""

import asyncio
import json
import os
import re
import sys

import httpx

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.5-flash"
API_BASE = os.environ.get("API_BASE_URL", "https://api.bigotesypaticas.com")

DRY_RUN = "--dry-run" in sys.argv
LIMIT = None
for arg in sys.argv:
    if arg.startswith("--limit="):
        LIMIT = int(arg.split("=")[1])

STRATEGIC_KEYWORDS = [
    # Geografía + producto
    {
        "keyword": "comida perros Pereira",
        "slug": "comida-perros-pereira",
        "geo": "Pereira",
        "category_slug": "perros",
    },
    {
        "keyword": "comida gatos Pereira",
        "slug": "comida-gatos-pereira",
        "geo": "Pereira",
        "category_slug": "gatos",
    },
    {
        "keyword": "concentrado perro Dosquebradas",
        "slug": "concentrado-perro-dosquebradas",
        "geo": "Dosquebradas",
        "category_slug": "perros",
    },
    {
        "keyword": "concentrado gato Dosquebradas",
        "slug": "concentrado-gato-dosquebradas",
        "geo": "Dosquebradas",
        "category_slug": "gatos",
    },
    {
        "keyword": "domicilio mascotas Pereira",
        "slug": "domicilio-mascotas-pereira",
        "geo": "Pereira",
        "category_slug": "todos",
    },
    {
        "keyword": "domicilio mascotas Dosquebradas",
        "slug": "domicilio-mascotas-dosquebradas",
        "geo": "Dosquebradas",
        "category_slug": "todos",
    },
    {
        "keyword": "tienda mascotas Risaralda",
        "slug": "tienda-mascotas-risaralda",
        "geo": "Risaralda",
        "category_slug": "todos",
    },
    {
        "keyword": "veterinaria Pereira productos",
        "slug": "veterinaria-pereira-productos",
        "geo": "Pereira",
        "category_slug": "todos",
    },
    # Marca + ciudad
    {
        "keyword": "Hills Pereira",
        "slug": "hills-pereira",
        "geo": "Pereira",
        "category_slug": "perros",
    },
    {
        "keyword": "Royal Canin Pereira",
        "slug": "royal-canin-pereira",
        "geo": "Pereira",
        "category_slug": "perros",
    },
    {
        "keyword": "Pro Plan Dosquebradas",
        "slug": "pro-plan-dosquebradas",
        "geo": "Dosquebradas",
        "category_slug": "perros",
    },
    {
        "keyword": "Bravecto Pereira",
        "slug": "bravecto-pereira",
        "geo": "Pereira",
        "category_slug": "medicamentos",
    },
    {
        "keyword": "Frontline Pereira",
        "slug": "frontline-pereira",
        "geo": "Pereira",
        "category_slug": "medicamentos",
    },
    # Tipo + edad
    {
        "keyword": "comida cachorro Pereira",
        "slug": "comida-cachorro-pereira",
        "geo": "Pereira",
        "category_slug": "perros",
    },
    {
        "keyword": "comida gato senior",
        "slug": "comida-gato-senior",
        "geo": None,
        "category_slug": "gatos",
    },
    {
        "keyword": "concentrado puppy razas pequeñas",
        "slug": "concentrado-puppy-razas-pequenas",
        "geo": None,
        "category_slug": "perros",
    },
    # Servicios
    {
        "keyword": "grooming Dosquebradas",
        "slug": "grooming-dosquebradas",
        "geo": "Dosquebradas",
        "category_slug": "accesorios",
    },
    {
        "keyword": "baño perros Pereira",
        "slug": "bano-perros-pereira",
        "geo": "Pereira",
        "category_slug": "accesorios",
    },
    {
        "keyword": "vacunación gatos Pereira",
        "slug": "vacunacion-gatos-pereira",
        "geo": "Pereira",
        "category_slug": "medicamentos",
    },
    # Categorías
    {
        "keyword": "accesorios perros Colombia",
        "slug": "accesorios-perros-colombia",
        "geo": None,
        "category_slug": "accesorios",
    },
    {
        "keyword": "juguetes perros premium",
        "slug": "juguetes-perros-premium",
        "geo": None,
        "category_slug": "accesorios",
    },
    {
        "keyword": "camas perros grandes",
        "slug": "camas-perros-grandes",
        "geo": None,
        "category_slug": "accesorios",
    },
    {
        "keyword": "antipulgas perros Colombia",
        "slug": "antipulgas-perros-colombia",
        "geo": None,
        "category_slug": "medicamentos",
    },
    # Diferenciadores únicos
    {
        "keyword": "app mascotas Colombia",
        "slug": "app-mascotas-colombia",
        "geo": None,
        "category_slug": "todos",
    },
    {
        "keyword": "carnet digital mascota",
        "slug": "carnet-digital-mascota",
        "geo": None,
        "category_slug": "todos",
    },
    {
        "keyword": "puntos fidelidad mascotas",
        "slug": "puntos-fidelidad-mascotas",
        "geo": None,
        "category_slug": "todos",
    },
    {
        "keyword": "portal cliente veterinaria",
        "slug": "portal-cliente-veterinaria",
        "geo": None,
        "category_slug": "todos",
    },
    # Barrios Pereira
    {
        "keyword": "mascotas Pinares Pereira",
        "slug": "mascotas-pinares-pereira",
        "geo": "Pinares, Pereira",
        "category_slug": "todos",
    },
    {
        "keyword": "mascotas Cuba Pereira",
        "slug": "mascotas-cuba-pereira",
        "geo": "Cuba, Pereira",
        "category_slug": "todos",
    },
    {
        "keyword": "mascotas Belmonte Pereira",
        "slug": "mascotas-belmonte-pereira",
        "geo": "Belmonte, Pereira",
        "category_slug": "todos",
    },
    # Barrios Dosquebradas
    {
        "keyword": "mascotas La Capilla Dosquebradas",
        "slug": "mascotas-la-capilla-dosquebradas",
        "geo": "La Capilla, Dosquebradas",
        "category_slug": "todos",
    },
    {
        "keyword": "mascotas Frailes Dosquebradas",
        "slug": "mascotas-frailes-dosquebradas",
        "geo": "Frailes, Dosquebradas",
        "category_slug": "todos",
    },
    # Preguntas
    {
        "keyword": "precio concentrado perro Pereira",
        "slug": "precio-concentrado-perro-pereira",
        "geo": "Pereira",
        "category_slug": "perros",
    },
    {
        "keyword": "dónde comprar comida mascotas Dosquebradas",
        "slug": "donde-comprar-comida-mascotas-dosquebradas",
        "geo": "Dosquebradas",
        "category_slug": "todos",
    },
    {
        "keyword": "mejor tienda mascotas Pereira",
        "slug": "mejor-tienda-mascotas-pereira",
        "geo": "Pereira",
        "category_slug": "todos",
    },
    # Comparativos
    {
        "keyword": "Hills vs Royal Canin perros",
        "slug": "hills-vs-royal-canin-perros",
        "geo": None,
        "category_slug": "perros",
    },
    {
        "keyword": "Pro Plan vs Eukanuba",
        "slug": "pro-plan-vs-eukanuba",
        "geo": None,
        "category_slug": "perros",
    },
    # Urgentes / problema
    {
        "keyword": "garrapatas perro qué hacer",
        "slug": "garrapatas-perro-que-hacer",
        "geo": None,
        "category_slug": "medicamentos",
    },
    {
        "keyword": "mi gato no come qué hago",
        "slug": "gato-no-come-que-hago",
        "geo": None,
        "category_slug": "gatos",
    },
    {
        "keyword": "primeros auxilios mascotas Pereira",
        "slug": "primeros-auxilios-mascotas-pereira",
        "geo": "Pereira",
        "category_slug": "medicamentos",
    },
]

PROMPT_LANDING = """Eres experto en SEO y copywriting para e-commerce de mascotas en Colombia.
Escribe contenido optimizado para la landing page de Bigotes y Paticas, tienda premium ubicada en
Dosquebradas, Risaralda, con domicilio a toda Pereira y Dosquebradas.

KEYWORD OBJETIVO: {keyword}
FOCO GEOGRÁFICO: {geo}
CATEGORÍA DE PRODUCTOS: {category_slug}

INSTRUCCIONES:
- intro_content: HTML de 300-400 palabras con h2, p, ul/li, strong. Optimizado para la keyword.
  Menciona naturalmente la ciudad/barrio. Explica beneficios de comprar en Bigotes y Paticas.
  NO hagas listas de servicios que no ofrece (solo productos y domicilio).
- title: 50-65 chars SEO con keyword y "Bigotes y Paticas"
- h1: 40-70 chars llamativo que incluya la keyword
- meta_description: 140-160 chars con CTA y keyword
- cta_text: Frase de acción corta (max 50 chars) ej: "Ver concentrados para perros →"

DEVUELVE SOLO JSON VÁLIDO (sin markdown):
{{
  "title": "...",
  "h1": "...",
  "meta_description": "...",
  "intro_content": "<h2>...</h2><p>...</p>...",
  "cta_text": "..."
}}"""


async def call_ai(client: httpx.AsyncClient, kw: dict) -> dict | None:
    prompt = PROMPT_LANDING.format(
        keyword=kw["keyword"],
        geo=kw.get("geo") or "toda Colombia",
        category_slug=kw.get("category_slug") or "general",
    )

    if DRY_RUN:
        print(f"  [DRY RUN] prompt {len(prompt)} chars")
        return None

    for attempt in range(3):
        try:
            res = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.65,
                    "max_tokens": 2048,
                },
                timeout=90,
            )
            res.raise_for_status()
            raw = res.json()["choices"][0]["message"]["content"].strip()
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                raw = match.group()
            return json.loads(raw)
        except Exception as e:
            print(f"  ⚠ Intento {attempt + 1}/3: {e}")
            if attempt < 2:
                await asyncio.sleep(4)
    return None


async def save_landing(client: httpx.AsyncClient, data: dict, kw: dict) -> bool:
    payload = {
        "slug": kw["slug"],
        "target_keyword": kw["keyword"],
        "title": data.get("title", kw["keyword"]),
        "h1": data.get("h1", kw["keyword"]),
        "meta_description": data.get("meta_description"),
        "intro_content": data.get("intro_content"),
        "category_slug": kw.get("category_slug"),
        "geographic_focus": kw.get("geo"),
        "cta_text": data.get("cta_text"),
        "is_active": True,
        "ai_model": MODEL,
    }
    try:
        res = await client.post(f"{API_BASE}/v1/landings", json=payload, timeout=30)
        res.raise_for_status()
        return True
    except Exception as e:
        print(f"  ✗ Error guardando: {e}")
        return False


async def main():
    if not OPENROUTER_API_KEY and not DRY_RUN:
        print("✗ OPENROUTER_API_KEY no configurada")
        sys.exit(1)

    keywords = STRATEGIC_KEYWORDS[:LIMIT] if LIMIT else STRATEGIC_KEYWORDS
    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Generando {len(keywords)} landings con {MODEL}")
    print(f"API target: {API_BASE}")
    print("─" * 60)

    ok = errors = 0

    async with httpx.AsyncClient(timeout=90) as client:
        for i, kw in enumerate(keywords, 1):
            print(f"\n[{i}/{len(keywords)}] {kw['keyword']}")
            data = await call_ai(client, kw)
            if not data:
                if not DRY_RUN:
                    errors += 1
                continue

            print(f"  h1: {data.get('h1', 'N/A')[:60]}")
            print(f"  content: {len(data.get('intro_content', ''))} chars")

            if await save_landing(client, data, kw):
                print(f"  ✓ Guardado → /landing/{kw['slug']}")
                ok += 1
            else:
                errors += 1

            if i < len(keywords):
                await asyncio.sleep(1.5)

    print(f"\n{'=' * 60}")
    if not DRY_RUN:
        print(f"✓ {ok} landings generadas")
        print(f"✗ {errors} errores")
        print("\nRevisa en: https://bigotesypaticas.com/landing/comida-perros-pereira")


if __name__ == "__main__":
    asyncio.run(main())
