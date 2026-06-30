#!/usr/bin/env python3
"""
Sincroniza reseñas de Google Business Profile → catalog.gbp_reviews_cache.
Uso: python scripts/sync_gbp_reviews.py

Requiere:
  GBP_PLACES_API_KEY  — clave de Google Places API con field "reviews"
  DATABASE_URL        — postgres DSN (mismo que el backend)

Lógica:
  1. Llama Places Details para obtener hasta 5 reseñas más recientes
  2. Inserta/actualiza en gbp_reviews_cache (upsert por reviewer_name + rating + created_at)
  3. Intenta fuzzy-match automático con portal.customers por phone/name
  4. Si hay match → acredita 50 pts (reason='gbp_review') si aún no se acreditaron
"""

import asyncio
import hashlib
import os
import sys
from datetime import UTC, datetime

import asyncpg
import httpx
from rapidfuzz import fuzz

PLACE_ID = "ChIJP6-g7Y1gR44RiKlIhE1zS_A"  # Bigotes y Paticas Google Place ID
API_KEY = os.environ.get("GBP_PLACES_API_KEY", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

PLACES_URL = "https://maps.googleapis.com/maps/api/place/details/json"
FIELDS = "reviews,rating,user_ratings_total"

# Umbral para fuzzy match de nombre (0-100)
FUZZY_THRESHOLD = 72


async def fetch_gbp_reviews() -> dict:
    params = {
        "place_id": PLACE_ID,
        "fields": FIELDS,
        "key": API_KEY,
        "language": "es",
        "reviews_sort": "newest",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(PLACES_URL, params=params)
        r.raise_for_status()
        data = r.json()
    if data.get("status") != "OK":
        raise RuntimeError(
            f"Places API error: {data.get('status')} — {data.get('error_message', '')}"
        )
    return data["result"]


def stable_id(reviewer: str, rating: int, ts: int) -> str:
    """Genera un ID estable para deduplicar."""
    raw = f"{reviewer}:{rating}:{ts}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def fuzzy_match_customer(conn: asyncpg.Connection, name: str) -> str | None:
    rows = await conn.fetch(
        "SELECT id, full_name FROM portal.customers WHERE full_name IS NOT NULL LIMIT 500"
    )
    best_score, best_id = 0, None
    for row in rows:
        score = fuzz.token_sort_ratio(name.lower(), row["full_name"].lower())
        if score > best_score:
            best_score, best_id = score, str(row["id"])
    return best_id if best_score >= FUZZY_THRESHOLD else None


async def award_gbp_points(conn: asyncpg.Connection, customer_id: str, gbp_review_id: str):
    already = await conn.fetchval(
        "SELECT 1 FROM portal.loyalty_points WHERE customer_id=$1::uuid AND description LIKE $2 LIMIT 1",
        customer_id,
        f"%{gbp_review_id}%",
    )
    if already:
        return
    await conn.execute(
        """
        INSERT INTO portal.loyalty_points (customer_id, points, reason, description, expires_at)
        VALUES ($1::uuid, 50, 'gbp_review', $2, NOW() + INTERVAL '1 year')
        """,
        customer_id,
        f"Reseña Google Business #{gbp_review_id}",
    )
    print(f"  ✅ 50 pts acreditados a cliente {customer_id}")


async def main():
    if not API_KEY:
        print("⚠️  GBP_PLACES_API_KEY no configurada — saliendo")
        sys.exit(0)
    if not DATABASE_URL:
        print("❌ DATABASE_URL requerida")
        sys.exit(1)

    print("📡 Obteniendo reseñas de Google Business Profile…")
    result = await fetch_gbp_reviews()

    overall_rating = result.get("rating")
    total_ratings = result.get("user_ratings_total", 0)
    reviews = result.get("reviews", [])

    print(f"⭐ Rating global: {overall_rating} ({total_ratings} reseñas)")
    print(f"📥 {len(reviews)} reseñas a procesar")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        inserted = 0
        matched = 0

        for rev in reviews:
            reviewer = rev.get("author_name", "Anónimo")
            rating = int(rev.get("rating", 0))
            comment = rev.get("text", "")
            ts = int(rev.get("time", 0))
            gbp_id = stable_id(reviewer, rating, ts)
            created_at = datetime.fromtimestamp(ts, tz=UTC)
            photo_url = rev.get("profile_photo_url")

            # Upsert en gbp_reviews_cache
            existing = await conn.fetchval(
                "SELECT id FROM catalog.gbp_reviews_cache WHERE gbp_review_id=$1 LIMIT 1", gbp_id
            )
            if existing:
                print(f"  ↩ Ya existe: {reviewer} ({rating}⭐)")
                continue

            # Intentar match con cliente
            customer_id = await fuzzy_match_customer(conn, reviewer)
            if customer_id:
                matched += 1
                print(f"  🔗 Match: {reviewer} → customer {customer_id}")

            await conn.execute(
                """
                INSERT INTO catalog.gbp_reviews_cache
                  (gbp_review_id, reviewer_name, reviewer_photo_url, rating, comment,
                   created_at, matched_customer_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7::uuid)
                """,
                gbp_id,
                reviewer,
                photo_url,
                rating,
                comment,
                created_at,
                customer_id,
            )
            inserted += 1
            print(f"  ✨ Insertada: {reviewer} ({rating}⭐)")

            # Acreditar puntos si hay match
            if customer_id:
                await award_gbp_points(conn, customer_id, gbp_id)

        print(f"\n✅ Sync completado: {inserted} nuevas, {matched} matcheadas con clientes")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
