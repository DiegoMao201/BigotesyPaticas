#!/usr/bin/env python3
"""
Generación masiva de 30 artículos de blog con IA — Bigotes y Paticas.

Uso:
  python scripts/generate_blog_posts.py --dry-run          # Muestra el prompt sin llamar la API
  python scripts/generate_blog_posts.py --limit=3          # Genera solo 3 artículos
  python scripts/generate_blog_posts.py                    # Genera los 30 completos

Requisitos:
  OPENROUTER_API_KEY = key de OpenRouter
  DATABASE_URL       = postgresql+asyncpg://...

Costo estimado: 30 artículos × ~3000 tokens output = ~$0.03 USD con Gemini 2.5 Flash
"""
import os
import sys
import json
import asyncio
import httpx
import re
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.5-flash"
API_BASE = os.environ.get("API_BASE_URL", "https://api.bigotesypaticas.com")

DRY_RUN = "--dry-run" in sys.argv
LIMIT = None
for arg in sys.argv:
    if arg.startswith("--limit="):
        LIMIT = int(arg.split("=")[1])

# ── Temas estratégicos ────────────────────────────────────────────────────────
BLOG_TOPICS = [
    # Nutrición
    {"title": "¿Cuántas veces al día debe comer un cachorro?", "category": "nutricion", "keyword": "alimentación cachorro"},
    {"title": "Mejor concentrado para perro adulto en Colombia 2026", "category": "nutricion", "keyword": "concentrado perro adulto"},
    {"title": "Hill's vs Royal Canin: ¿cuál es mejor para mi perro?", "category": "nutricion", "keyword": "Hills vs Royal Canin"},
    {"title": "Snacks para perros: cuáles son seguros y cuáles no", "category": "nutricion", "keyword": "snacks perros seguros"},
    {"title": "Alimentos peligrosos para gatos que tienes en casa", "category": "nutricion", "keyword": "alimentos peligrosos gatos"},
    {"title": "Concentrado por bulto vs por libra: ¿qué conviene más?", "category": "nutricion", "keyword": "concentrado bulto vs libra"},
    # Salud
    {"title": "Calendario completo de vacunación canina en Colombia", "category": "salud", "keyword": "vacunas perros Colombia"},
    {"title": "Calendario de vacunación felina explicado paso a paso", "category": "salud", "keyword": "vacunas gatos"},
    {"title": "Síntomas de pulgas en perros y cómo eliminarlas definitivamente", "category": "salud", "keyword": "pulgas perros"},
    {"title": "Mi perro no come: 5 razones y cuándo preocuparse", "category": "salud", "keyword": "perro no come"},
    {"title": "Mi gato vomita: ¿es normal o debo ir al veterinario?", "category": "salud", "keyword": "gato vomita"},
    {"title": "Cómo desparasitar a tu gato en casa paso a paso", "category": "salud", "keyword": "desparasitar gato"},
    # Cuidado
    {"title": "¿Cada cuánto bañar un perro? Guía completa por raza", "category": "cuidado", "keyword": "cada cuánto bañar perro"},
    {"title": "Grooming en casa: técnicas profesionales para tu perro", "category": "cuidado", "keyword": "grooming casa"},
    {"title": "Cómo cepillar a un gato persa sin pelearlo", "category": "cuidado", "keyword": "cepillar gato persa"},
    {"title": "Cómo cuidar a tu mascota en el clima cálido de Risaralda", "category": "cuidado", "keyword": "cuidar mascota clima cálido"},
    # Razas populares
    {"title": "Guía completa del Yorkshire Terrier en clima cálido", "category": "razas", "keyword": "Yorkshire Pereira"},
    {"title": "Schnauzer Miniatura: cuidados esenciales y alimentación", "category": "razas", "keyword": "Schnauzer mini cuidados"},
    {"title": "Gato Persa: el compañero ideal para apartamento", "category": "razas", "keyword": "gato persa cuidados"},
    {"title": "French Poodle Mini: alimentación, peluquería y cuidados", "category": "razas", "keyword": "french poodle"},
    {"title": "Bulldog Francés en Colombia: lo que debes saber antes de adoptar", "category": "razas", "keyword": "bulldog francés Colombia"},
    # Local Pereira/Dosquebradas
    {"title": "Veterinarias 24 horas en Pereira y Dosquebradas: guía completa", "category": "local", "keyword": "veterinaria 24 horas Pereira"},
    {"title": "Mejores parques para perros en Pereira (actualizado 2026)", "category": "local", "keyword": "parque perros Pereira"},
    {"title": "Adopción de mascotas en Risaralda: dónde y cómo hacerlo", "category": "local", "keyword": "adopción mascotas Risaralda"},
    {"title": "Restaurantes pet-friendly en Pereira para ir con tu perro", "category": "local", "keyword": "restaurantes pet friendly Pereira"},
    {"title": "Hospedaje de mascotas en Pereira para las vacaciones", "category": "local", "keyword": "hotel mascotas Pereira"},
    # Comportamiento
    {"title": "Por qué mi perro ladra todo el tiempo y cómo corregirlo", "category": "comportamiento", "keyword": "perro ladra todo el tiempo"},
    {"title": "Mi gato araña los muebles: solución definitiva", "category": "comportamiento", "keyword": "gato araña muebles"},
    {"title": "Adiestramiento básico para cachorros: los 5 comandos esenciales", "category": "comportamiento", "keyword": "adiestramiento cachorro"},
    # General
    {"title": "Cuánto cuesta tener un perro al mes en Colombia 2026", "category": "general", "keyword": "cuánto cuesta tener perro Colombia"},
]

PROMPT_BLOG = '''Eres un veterinario experto que escribe para Bigotes y Paticas, tienda
premium de mascotas ubicada en Dosquebradas, Risaralda (Colombia), con domicilio a toda
la zona urbana de Pereira y Dosquebradas.

TEMA DEL ARTÍCULO: {title}
CATEGORÍA: {category}
PALABRA CLAVE PRINCIPAL: {keyword}

REQUISITOS DEL ARTÍCULO:
- Entre 800 y 1200 palabras de contenido real, informativo y útil
- Tono cálido, profesional y autoritativo (como un veterinario de confianza)
- Español de Colombia (no de España): usa "usted/tú" indistinto según contexto
- Estructura clara: introducción + H2 secciones (mínimo 3) + H3 subsecciones cuando aplique + conclusión
- Mencionar naturalmente "Pereira" o "Dosquebradas" 2-3 veces como contexto local
- Al final, incluir un CTA suave: "En Bigotes y Paticas tenemos los productos que necesitas"
- NO inventar datos clínicos específicos sin base
- NO mencionar marcas específicas de competidores locales
- Incluir consejos prácticos reales que den valor al lector

FORMATO DE RESPUESTA: JSON puro (sin markdown ni ```json```) con esta estructura exacta:
{{
  "slug": "url-amigable-en-kebab-case",
  "title": "{title}",
  "excerpt": "Resumen de 120-150 caracteres para preview de la tarjeta",
  "content": "<h2>...</h2><p>...</p>... (HTML completo del artículo, bien estructurado)",
  "category": "{category}",
  "keywords": ["keyword principal", "keyword 2 Pereira", "keyword 3 Colombia", "keyword 4", "keyword 5"],
  "meta_title": "Título SEO de 50-60 caracteres exactos con keyword",
  "meta_description": "Meta description de 140-160 caracteres con CTA natural",
  "cover_image_query": "Query en inglés para buscar foto de stock relevante"
}}

IMPORTANTE: El campo "content" debe ser HTML limpio con etiquetas h2, h3, p, ul, li, strong.
No uses clases CSS ni atributos extra. El texto debe tener al menos 800 palabras reales.'''


async def call_ai(client: httpx.AsyncClient, topic: dict) -> dict | None:
    prompt = PROMPT_BLOG.format(**topic)

    if DRY_RUN:
        print(f"\n[DRY RUN] {topic['title']}")
        print(f"Prompt preview (primeras 300 chars): {prompt[:300]}...")
        return None

    for attempt in range(3):
        try:
            res = await client.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
                timeout=120,
            )
            res.raise_for_status()
            raw = res.json()["choices"][0]["message"]["content"].strip()

            # Extraer JSON si viene envuelto en ```
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                raw = match.group()

            return json.loads(raw)
        except Exception as e:
            print(f"  ⚠ Intento {attempt + 1}/3 falló para '{topic['title']}': {e}")
            if attempt < 2:
                await asyncio.sleep(5)
    return None


async def save_post(client: httpx.AsyncClient, post_data: dict, topic: dict) -> bool:
    payload = {
        "slug": post_data.get("slug", ""),
        "title": post_data.get("title", topic["title"]),
        "excerpt": post_data.get("excerpt"),
        "content": post_data.get("content", ""),
        "category": post_data.get("category", topic["category"]),
        "keywords": post_data.get("keywords", []),
        "meta_title": post_data.get("meta_title"),
        "meta_description": post_data.get("meta_description"),
        "author": "Equipo Bigotes y Paticas",
        "ai_model": MODEL,
    }

    try:
        res = await client.post(
            f"{API_BASE}/v1/blog/posts",
            json=payload,
            timeout=30,
        )
        res.raise_for_status()
        return True
    except Exception as e:
        print(f"  ✗ Error guardando '{topic['title']}': {e}")
        return False


async def main():
    if not OPENROUTER_API_KEY and not DRY_RUN:
        print("✗ OPENROUTER_API_KEY no configurada")
        sys.exit(1)

    topics = BLOG_TOPICS[:LIMIT] if LIMIT else BLOG_TOPICS

    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Generando {len(topics)} artículos con {MODEL}")
    print(f"API target: {API_BASE}")
    print("─" * 60)

    ok = 0
    errors = 0

    async with httpx.AsyncClient(timeout=120) as client:
        for i, topic in enumerate(topics, 1):
            print(f"\n[{i}/{len(topics)}] {topic['title']}")

            post_data = await call_ai(client, topic)

            if not post_data:
                if not DRY_RUN:
                    errors += 1
                continue

            # Preview
            print(f"  slug: {post_data.get('slug', 'N/A')}")
            print(f"  meta_title: {post_data.get('meta_title', 'N/A')}")
            content_len = len(post_data.get('content', ''))
            print(f"  content: {content_len} chars HTML")

            saved = await save_post(client, post_data, topic)
            if saved:
                print(f"  ✓ Guardado")
                ok += 1
            else:
                errors += 1

            # Pausa entre requests para no saturar la API
            if i < len(topics):
                await asyncio.sleep(2)

    print("\n" + "═" * 60)
    if not DRY_RUN:
        print(f"✓ {ok} artículos generados y guardados")
        print(f"✗ {errors} errores")
        print(f"\nRevisa el blog en: https://bigotesypaticas.com/blog")
    else:
        print(f"[DRY RUN completado] Nada fue enviado a la API")


if __name__ == "__main__":
    asyncio.run(main())
