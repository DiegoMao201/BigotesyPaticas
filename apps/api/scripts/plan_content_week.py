#!/usr/bin/env python3
"""Job de planificación semanal de contenido — Sprint 6A.

Corre lunes a las 5am:
  0 5 * * 1 docker exec <api> python scripts/plan_content_week.py

Genera 10-12 posts para la semana con distribución editorial y datos reales de la DB.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_BOGOTA = ZoneInfo("America/Bogota")

# Permitir imports desde /app
sys.path.insert(0, "/app")

try:
    import psycopg2
except ModuleNotFoundError:
    import psycopg as psycopg2  # type: ignore[no-redef]

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DB_URL = (
    os.environ.get("DATABASE_URL_SYNC", "")
    .replace("postgresql+psycopg://", "postgresql://")
    .replace("postgresql+asyncpg://", "postgresql://")
)


def get_engine_config(cur) -> dict:
    cur.execute("SELECT key, value FROM content.engine_config")
    return {r[0]: r[1] for r in cur.fetchall()}


def get_top_products(cur, limit=10) -> list[dict]:
    cur.execute(
        """
        SELECT p.id::text as product_id, p.sku, p.name, p.slug, p.price,
               -- Preferir imagen transparente (sin fondo blanco) cuando existe
               COALESCE(p.image_url_transparent, p.primary_image_url) as product_image_url,
               p.image_url_transparent IS NOT NULL as has_transparent,
               c.name as category_name
        FROM catalog.products p
        LEFT JOIN catalog.categories c ON c.id = p.category_id
        WHERE p.is_active = true AND p.is_published = true
          AND p.primary_image_url IS NOT NULL
        ORDER BY
          -- Priorizar productos con fondo transparente para mejor composición
          (p.image_url_transparent IS NOT NULL) DESC,
          RANDOM()
        LIMIT %s
    """,
        (limit,),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]


def get_recent_reviews(cur, limit=3) -> list[dict]:
    cur.execute(
        """
        SELECT r.rating, r.comment, r.title, r.pet_name,
               c.full_name,
               p.name as product_name
        FROM catalog.product_reviews r
        LEFT JOIN crm.customers c ON c.id = r.customer_id
        LEFT JOIN catalog.products p ON p.id = r.product_id
        WHERE r.status IN ('approved','auto_published') AND r.rating >= 4
        ORDER BY r.created_at DESC
        LIMIT %s
    """,
        (limit,),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]


_WEEK_PLAN_21 = [
    # (day_offset, hour, minute, template_code, context_key)
    # Lunes
    (0, 7, 30, "product_hero", "product"),
    (0, 12, 30, "educational_data", "educational"),
    (0, 19, 0, "awareness_adoption", "awareness"),
    # Martes
    (1, 7, 30, "expert_tip", "educational"),
    (1, 12, 30, "product_with_purpose", "product"),
    (1, 19, 0, "review_typographic", "review"),
    # Miércoles
    (2, 7, 30, "educational_data", "educational"),
    (2, 12, 30, "sterilization_awareness", "awareness"),
    (2, 19, 0, "product_hero", "product"),
    # Jueves
    (3, 7, 30, "reminder_service", "reminder"),
    (3, 12, 30, "expert_tip", "educational"),
    (3, 19, 0, "portal_promotion", "portal"),
    # Viernes
    (4, 7, 30, "product_hero", "product"),
    (4, 12, 30, "educational_data", "educational"),
    (4, 19, 0, "domicilio_pereira_dosquebradas", "domicilio"),
    # Sábado
    (5, 9, 0, "product_with_purpose", "product"),
    (5, 13, 0, "local_eje_cafetero", "local"),
    (5, 18, 0, "awareness_adoption", "awareness"),
    # Domingo
    (6, 10, 0, "review_typographic", "review"),
    (6, 15, 0, "educational_data", "educational"),
    (6, 19, 0, "product_hero", "product"),
]


def build_week_plan(products: list, reviews: list) -> list[dict]:
    """Construye el plan semanal de 21 posts con distribución lun-dom."""
    product_idx = 0
    review_idx = 0

    # Usar hora Colombia para que 7:30, 12:30, 19:00 coincidan con hora local
    today = datetime.now(_BOGOTA).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    days_until_monday = (7 - today.weekday()) % 7 or 7
    week_start = today + timedelta(days=days_until_monday)

    result = []
    for day_offset, hour, minute, template_code, ctx_key in _WEEK_PLAN_21:
        # Si no hay reseñas, sustituir review_typographic por awareness_adoption
        if ctx_key == "review" and not reviews:
            template_code = "awareness_adoption"
            ctx_key = "awareness"

        scheduled_day = week_start + timedelta(days=day_offset)
        scheduled_at = scheduled_day.replace(hour=hour, minute=minute, second=0, microsecond=0)

        context = _build_context(ctx_key, products, reviews, product_idx, review_idx)
        if ctx_key == "product" and products:
            product_idx = (product_idx + 1) % len(products)
        if ctx_key == "review" and reviews:
            review_idx = (review_idx + 1) % len(reviews)

        result.append(
            {
                "template_code": template_code,
                "context": context,
                "scheduled_at": scheduled_at.replace(tzinfo=None).isoformat(),
            }
        )

    return result


_EDUCATIONAL_TOPICS = [
    {
        "key_data": "38%",
        "topic": "de perros en Colombia presentan sobrepeso, según estudios nutricionales regionales",
    },
    {
        "key_data": "72 h",
        "topic": "es el tiempo máximo sin agua que tolera un gato adulto antes de sufrir daño renal irreversible",
    },
    {
        "key_data": "2 kg",
        "topic": "de sobrepeso equivalen a 20 kg de presión extra en las articulaciones de un perro mediano",
    },
    {
        "key_data": "3x",
        "topic": "más riesgo de diabetes tienen los gatos castrados sin ajuste en su dieta calórica",
    },
    {
        "key_data": "6 min",
        "topic": "es el tiempo que tarda el calor en ser letal para un perro dentro de un carro con ventanas cerradas",
    },
    {
        "key_data": "80%",
        "topic": "de perros mayores de 3 años presentan algún grado de enfermedad periodontal",
    },
    {
        "key_data": "1 de 4",
        "topic": "gatos domésticos en Colombia desarrolla cálculos urinarios vinculados a dieta seca y poca hidratación",
    },
    {
        "key_data": "17%",
        "topic": "de gatos domésticos en Latinoamérica son alimentados con croquetas inadecuadas para su etapa de vida",
    },
]


def _build_context(key: str, products: list, reviews: list, pidx: int, ridx: int) -> dict:
    import random

    if key == "product" and products:
        p = products[pidx % len(products)]
        return {
            # SOLO datos reales de la DB — no inventar variantes, precios ni características
            "product_name": p["name"],           # Nombre EXACTO — no modificar
            "product_price": float(p["price"] or 0),  # Precio REAL en COP
            "slug": p["slug"],                   # Slug real para URL /producto/{slug}
            "category": p.get("category_name", ""),
            "product_image_url": p.get("product_image_url", ""),
            "product_id": p.get("product_id", ""),
        }
    if key == "review" and reviews:
        r = reviews[ridx % len(reviews)]
        name = (r.get("full_name") or "Cliente").strip().split()[0]
        return {
            "customer_first_name": name,
            "customer_location": "Pereira",
            "review_quote_short": (r.get("comment") or r.get("title") or "Excelente producto")[:80],
            "review_quote_full": r.get("comment")
            or r.get("title")
            or "Muy buena calidad y atención.",
            "product_name": r.get("product_name", ""),
        }
    if key == "educational":
        t = random.choice(_EDUCATIONAL_TOPICS)
        return {
            "key_data": t["key_data"],
            "topic_detail": t["topic"],
            "topic_hashtags": "#NutriciónAnimal",
        }
    if key == "awareness":
        return {
            "local_context": "Pereira y Dosquebradas",
            "animal_type": "perros y gatos callejeros",
            # IMPORTANTE: Bigotes y Paticas NO apoya fundaciones, NO hace jornadas
            # de adopción, NO dona por compra, NO trabaja con refugios.
            # Solo comparte datos reales de la realidad animal local.
            "tone": "informativo y empático — compartimos datos reales, NO afirmamos apoyar fundaciones, adopciones, refugios ni donaciones",
        }
    if key == "reminder":
        return {
            "service": "vacunación anual",
            "timing": "cada 12 meses para refuerzo antirrábico y polivalente",
            "products": "vacunas y antiparasitarios",
        }
    if key == "local":
        return {
            "city": "Pereira / Dosquebradas",
            "climate": "clima templado del Eje Cafetero",
            "differentiator": "selección de productos adaptados al trópico colombiano",
        }
    if key == "portal":
        return {
            "feature": "Puntos Bigotes",
            "benefit": "acumulá puntos con cada compra y canjeá por descuentos",
            "url": "mi.bigotesypaticas.com",
        }
    if key == "domicilio":
        return {
            "delivery_area": "Pereira y Dosquebradas",
            "min_order_free": "30.000",
            "delivery_fee_small": "5.000",
        }
    return {}


async def run():
    if not DB_URL:
        print("❌ DATABASE_URL_SYNC no configurada", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(DB_URL, connect_timeout=10)
    cur = conn.cursor()

    # 1. Verificar kill-switch
    cfg = get_engine_config(cur)
    if cfg.get("is_active") != "true":
        print("⏸  Engine inactivo (is_active=false) — no se genera nada")
        conn.close()
        return
    if cfg.get("weekly_generation_enabled") != "true":
        print("⏸  Generación semanal deshabilitada (weekly_generation_enabled=false)")
        conn.close()
        return

    print("✅ Engine activo — iniciando plan semanal...")

    # 2. Source data
    products = get_top_products(cur)
    reviews = get_recent_reviews(cur)
    print(f"   📦 {len(products)} productos top")
    print(f"   ⭐ {len(reviews)} reseñas recientes")

    # 3. Construir plan
    plan = build_week_plan(products, reviews)
    print(f"\n   📅 {len(plan)} posts planificados para la semana\n")

    conn.close()

    # 4. Generar posts via API del servicio (async)
    import httpx

    # Usar la API HTTP local para no duplicar lógica de DB
    api_base = "http://localhost:8000"
    generated = failed = 0

    async with httpx.AsyncClient(timeout=120) as client:
        # Obtener token admin
        r = await client.post(
            f"{api_base}/v1/auth/login",
            json={
                "email": os.environ.get("ADMIN_EMAIL", ""),
                "password": os.environ.get("ADMIN_PASSWORD", ""),
            },
        )
        if r.status_code != 200:
            print(f"❌ Login admin fallido: {r.text}", file=sys.stderr)
            sys.exit(1)
        token = r.json().get("access_token", "")

        for item in plan:
            try:
                resp = await client.post(
                    f"{api_base}/v1/admin/content/generate",
                    json={
                        "template_code": item["template_code"],
                        "context": item["context"],
                        "scheduled_at": item["scheduled_at"],
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 201:
                    post = resp.json()
                    print(
                        f"   ✅ [{item['template_code']}] {post.get('id','')[:8]}… → {item['scheduled_at'][:10]}"
                    )
                    generated += 1
                else:
                    print(f"   ❌ [{item['template_code']}] {resp.status_code} {resp.text[:100]}")
                    failed += 1
            except Exception as e:
                print(f"   ❌ [{item['template_code']}] Error: {e}")
                failed += 1

    print(f"\n{'─'*50}")
    print(f"✅ Generados: {generated}")
    print(f"❌ Fallidos:  {failed}")

    # 5. Notificación WhatsApp (simplificado — usa endpoint admin si queda tiempo)
    if generated > 0:
        print(
            f"\n📱 {generated} posts pendientes de aprobación en admin.bigotesypaticas.com/content/calendar"
        )


if __name__ == "__main__":
    asyncio.run(run())
