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
from datetime import datetime, timezone

import asyncpg
import httpx
from rapidfuzz import fuzz

PLACE_ID = os.environ.get("GBP_PLACE_ID", "ChIJUbZRoXGBOI4R8vrs6AsH7XQ")  # Mall Zamara Plaza
API_KEY = os.environ.get("GBP_PLACES_API_KEY", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

PLACES_NEW_URL = f"https://places.googleapis.com/v1/places/{PLACE_ID}"

# Umbral para fuzzy match de nombre (0-100)
FUZZY_THRESHOLD = 72


async def fetch_gbp_reviews() -> dict:
    """Usa Places API (New) — soporta hasta 5 reseñas recientes."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            PLACES_NEW_URL,
            headers={
                "X-Goog-Api-Key": API_KEY,
                "X-Goog-FieldMask": "id,displayName,rating,userRatingCount,reviews",
            },
            params={"languageCode": "es"},
        )
        r.raise_for_status()
        data = r.json()
    if "error" in data:
        raise RuntimeError(f"Places API error: {data['error'].get('message', data)}")
    # Normalizar al formato que espera el resto del script
    reviews_raw = data.get("reviews", [])
    reviews = []
    for rv in reviews_raw:
        reviews.append({
            "author_name": rv.get("authorAttribution", {}).get("displayName", "Anónimo"),
            "profile_photo_url": rv.get("authorAttribution", {}).get("photoUri"),
            "rating": rv.get("rating", 0),
            "text": rv.get("text", {}).get("text", ""),
            "time": rv.get("publishTime", ""),
        })
    return {
        "rating": data.get("rating"),
        "user_ratings_total": data.get("userRatingCount", 0),
        "reviews": reviews,
    }


def stable_id(reviewer: str, rating: int, ts: int) -> str:
    """Genera un ID estable para deduplicar."""
    raw = f"{reviewer}:{rating}:{ts}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def fuzzy_match_customer(conn: asyncpg.Connection, name: str) -> str | None:
    rows = await conn.fetch("SELECT id, full_name FROM crm.customers WHERE full_name IS NOT NULL LIMIT 500")
    best_score, best_id = 0, None
    for row in rows:
        score = fuzz.token_sort_ratio(name.lower(), row["full_name"].lower())
        if score > best_score:
            best_score, best_id = score, str(row["id"])
    return best_id if best_score >= FUZZY_THRESHOLD else None


async def award_gbp_points(conn: asyncpg.Connection, customer_id: str, gbp_review_id: str):
    already = await conn.fetchval(
        "SELECT points_credited FROM catalog.gbp_reviews_cache WHERE google_review_id=$1 LIMIT 1",
        gbp_review_id,
    )
    if already:
        return
    await conn.execute(
        """
        INSERT INTO portal.loyalty_points (customer_id, points, reason, description, expires_at)
        VALUES ($1::uuid, 50, 'gbp_review', $2, NOW() + INTERVAL '1 year')
        """,
        customer_id, f"Reseña Google Business #{gbp_review_id}",
    )
    await conn.execute(
        "UPDATE catalog.gbp_reviews_cache SET points_credited=1, points_credited_at=NOW() WHERE google_review_id=$1",
        gbp_review_id,
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

    conn = await asyncpg.connect(DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        inserted = 0
        matched = 0

        for rev in reviews:
            reviewer = rev.get("author_name", "Anónimo")
            rating = int(rev.get("rating", 0))
            comment = rev.get("text", "")
            time_raw = rev.get("time", "")
            # publishTime puede ser ISO string ("2024-03-15T...") o unix int
            if isinstance(time_raw, str) and time_raw:
                from dateutil.parser import parse as parse_dt
                created_at = parse_dt(time_raw).replace(tzinfo=timezone.utc) if "+" not in time_raw else parse_dt(time_raw)
                ts = int(created_at.timestamp())
            else:
                ts = int(time_raw) if time_raw else 0
                created_at = datetime.fromtimestamp(ts, tz=timezone.utc)
            gbp_id = stable_id(reviewer, rating, ts)
            photo_url = rev.get("profile_photo_url")

            # Upsert en gbp_reviews_cache (columna real: google_review_id)
            existing = await conn.fetchval(
                "SELECT id FROM catalog.gbp_reviews_cache WHERE google_review_id=$1 LIMIT 1", gbp_id
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
                  (google_review_id, reviewer_name, reviewer_photo_url, rating, comment,
                   review_created_at, matched_customer_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7::uuid)
                """,
                gbp_id, reviewer, photo_url, rating, comment, created_at,
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
