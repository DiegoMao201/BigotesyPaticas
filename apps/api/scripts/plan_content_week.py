#!/usr/bin/env python3
"""Job de planificación semanal de contenido — Sprint 6A.

Corre lunes a las 5am:
  0 5 * * 1 docker exec <api> python scripts/plan_content_week.py

Genera 10-12 posts para la semana con distribución editorial y datos reales de la DB.
"""
from __future__ import annotations

import json
import os
import sys
import asyncio
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Permitir imports desde /app
sys.path.insert(0, "/app")

try:
    import psycopg2
except ModuleNotFoundError:
    import psycopg as psycopg2  # type: ignore[no-redef]

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DB_URL = os.environ.get(
    "DATABASE_URL_SYNC", ""
).replace("postgresql+psycopg://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")


def get_engine_config(cur) -> dict:
    cur.execute("SELECT key, value FROM content.engine_config")
    return {r[0]: r[1] for r in cur.fetchall()}


def get_top_products(cur, limit=5) -> list[dict]:
    cur.execute("""
        SELECT p.sku, p.name, p.slug, p.price, c.name as category_name
        FROM catalog.products p
        LEFT JOIN catalog.categories c ON c.id = p.category_id
        WHERE p.is_active = true AND p.is_published = true
          AND p.primary_image_url IS NOT NULL
        ORDER BY p.created_at DESC
        LIMIT %s
    """, (limit,))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_recent_reviews(cur, limit=3) -> list[dict]:
    cur.execute("""
        SELECT r.rating, r.comment, r.title, r.pet_name,
               c.full_name,
               p.name as product_name
        FROM catalog.product_reviews r
        LEFT JOIN crm.customers c ON c.id = r.customer_id
        LEFT JOIN catalog.products p ON p.id = r.product_id
        WHERE r.status IN ('approved','auto_published') AND r.rating >= 4
        ORDER BY r.created_at DESC
        LIMIT %s
    """, (limit,))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def build_week_plan(products: list, reviews: list) -> list[dict]:
    """Construye el plan semanal con distribución por categoría."""
    # Distribución: 30% product, 25% educational, 20% awareness, 15% review, 10% otros
    plan = [
        # Lunes
        {"template_code": "product_hero",           "context_key": "product", "slot": "morning"},
        {"template_code": "educational_data",        "context_key": "educational", "slot": "evening"},
        # Martes
        {"template_code": "awareness_adoption",      "context_key": "awareness", "slot": "lunch"},
        {"template_code": "expert_tip",              "context_key": "educational", "slot": "evening"},
        # Miércoles
        {"template_code": "product_with_purpose",    "context_key": "product", "slot": "morning"},
        {"template_code": "review_typographic",      "context_key": "review", "slot": "lunch"},
        # Jueves
        {"template_code": "educational_data",        "context_key": "educational", "slot": "morning"},
        {"template_code": "reminder_service",        "context_key": "reminder", "slot": "lunch"},
        # Viernes
        {"template_code": "product_hero",            "context_key": "product", "slot": "evening"},
        {"template_code": "sterilization_awareness", "context_key": "awareness", "slot": "morning"},
        # Sábado
        {"template_code": "local_eje_cafetero",       "context_key": "local", "slot": "morning"},
        {"template_code": "portal_promotion",        "context_key": "portal", "slot": "lunch"},
    ]

    product_idx = 0
    review_idx = 0

    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    # Ir al próximo lunes
    days_until_monday = (7 - today.weekday()) % 7 or 7
    week_start = today + timedelta(days=days_until_monday)

    slot_hours = {"morning": 7, "lunch": 12, "evening": 19}
    slot_minutes = {"morning": 30, "lunch": 30, "evening": 0}

    result = []
    for i, item in enumerate(plan):
        day_offset = i // 2
        if day_offset >= 7:
            break
        scheduled_day = week_start + timedelta(days=day_offset)
        slot = item["slot"]
        scheduled_at = scheduled_day.replace(
            hour=slot_hours[slot], minute=slot_minutes[slot]
        )

        context = _build_context(
            item["context_key"],
            products, reviews, product_idx, review_idx
        )
        if item["context_key"] == "product" and products:
            product_idx = (product_idx + 1) % len(products)
        if item["context_key"] == "review" and reviews:
            review_idx = (review_idx + 1) % len(reviews)

        result.append({
            "template_code": item["template_code"],
            "context": context,
            "scheduled_at": scheduled_at.replace(tzinfo=None).isoformat(),
        })

    return result


def _build_context(key: str, products: list, reviews: list, pidx: int, ridx: int) -> dict:
    if key == "product" and products:
        p = products[pidx % len(products)]
        return {
            "product_name": p["name"],
            "product_price": float(p["price"] or 0),
            "slug": p["slug"],
            "category": p.get("category_name", ""),
            "key_benefit": f"Producto {p.get('category_name', 'para mascotas')} de alta calidad",
        }
    if key == "review" and reviews:
        r = reviews[ridx % len(reviews)]
        name = ((r.get("full_name") or "Cliente").strip().split()[0])
        return {
            "customer_first_name": name,
            "customer_location": "Pereira",
            "review_quote_short": (r.get("comment") or r.get("title") or "Excelente producto")[:80],
            "review_quote_full": r.get("comment") or r.get("title") or "Muy buena calidad y atención.",
            "product_name": r.get("product_name", ""),
        }
    if key == "educational":
        topics = [
            {"key_data": "38%", "topic": "perros en Colombia padecen obesidad según estudios regionales"},
            {"key_data": "72h", "topic": "tiempo máximo sin agua que tolera un gato adulto antes de daño renal"},
            {"key_data": "2kg", "topic": "diferencia en carga articular en perros con 2kg de sobrepeso"},
        ]
        import random
        t = random.choice(topics)
        return {"key_data": t["key_data"], "topic_detail": t["topic"], "topic_hashtags": "#NutriciónAnimal"}
    if key == "awareness":
        return {
            "local_context": "Pereira y Dosquebradas",
            "animal_type": "perros callejeros",
            "action": "apoyamos jornadas de adopción en Mall Zamara Plaza",
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
    reviews  = get_recent_reviews(cur)
    print(f"   📦 {len(products)} productos top")
    print(f"   ⭐ {len(reviews)} reseñas recientes")

    # 3. Construir plan
    plan = build_week_plan(products, reviews)
    print(f"\n   📅 {len(plan)} posts planificados para la semana\n")

    conn.close()

    # 4. Generar posts via API del servicio (async)
    from app.services.content_generator import ContentGenerator
    import httpx

    # Usar la API HTTP local para no duplicar lógica de DB
    api_base = "http://localhost:8000"
    generated = failed = 0

    async with httpx.AsyncClient(timeout=120) as client:
        # Obtener token admin
        r = await client.post(f"{api_base}/v1/auth/login",
            json={"email": os.environ.get("ADMIN_EMAIL",""), "password": os.environ.get("ADMIN_PASSWORD","")})
        if r.status_code != 200:
            print(f"❌ Login admin fallido: {r.text}", file=sys.stderr)
            sys.exit(1)
        token = r.json().get("access_token", "")

        for item in plan:
            try:
                resp = await client.post(
                    f"{api_base}/v1/admin/content/generate",
                    json={"template_code": item["template_code"], "context": item["context"],
                          "scheduled_at": item["scheduled_at"]},
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 201:
                    post = resp.json()
                    print(f"   ✅ [{item['template_code']}] {post.get('id','')[:8]}… → {item['scheduled_at'][:10]}")
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
        print(f"\n📱 {generated} posts pendientes de aprobación en admin.bigotesypaticas.com/content/calendar")


if __name__ == "__main__":
    asyncio.run(run())
