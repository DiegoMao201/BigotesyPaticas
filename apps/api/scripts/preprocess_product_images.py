#!/usr/bin/env python3
"""Procesa imágenes de productos con rembg vía Replicate para eliminar fondo blanco.

Idempotente: skip productos con image_url_transparent ya procesado.
Costo: ~$0.002/imagen vía Replicate.

Uso:
  docker exec <api> python scripts/preprocess_product_images.py        # todos
  docker exec <api> python scripts/preprocess_product_images.py --dry  # solo contar
"""
from __future__ import annotations

import asyncio
import io
import os
import sys
import logging
import time
from datetime import datetime

sys.path.insert(0, "/app")

try:
    import psycopg2
except ModuleNotFoundError:
    import psycopg as psycopg2  # type: ignore[no-redef]

import boto3
import replicate
import requests
from botocore.client import Config
from PIL import Image

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CDN_BUCKET   = os.environ.get("S3_BUCKET", "catalogo-ferreinox")
CDN_ENDPOINT = os.environ.get("S3_ENDPOINT_URL", "https://nyc3.digitaloceanspaces.com")
CDN_REGION   = os.environ.get("S3_REGION", "nyc3")
CDN_BASE     = os.environ.get("S3_PUBLIC_URL", "https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com")
S3_ACCESS    = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET    = os.environ.get("S3_SECRET_KEY", "")

DB_URL = os.environ.get("DATABASE_URL_SYNC", "").replace(
    "postgresql+psycopg://", "postgresql://"
).replace("postgresql+asyncpg://", "postgresql://")

REPLICATE_MODEL = "cjwbw/rembg:fb8af171cfa1616ddcf1242c093f9c46bcada5ad4cf6f2fbe8b81b330ec5c003"
COST_PER_IMAGE  = 0.002  # USD estimado


def s3_client():
    return boto3.client(
        "s3",
        region_name=CDN_REGION,
        endpoint_url=CDN_ENDPOINT,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        config=Config(signature_version="s3v4"),
    )


def remove_background(replicate_client, image_url: str) -> bytes | None:
    """Llama a rembg en Replicate. Retorna PNG bytes con transparencia."""
    try:
        output = replicate_client.run(
            REPLICATE_MODEL,
            input={"image": image_url},
        )
        result_url = str(output) if not isinstance(output, list) else str(output[0])
        resp = requests.get(result_url, timeout=60)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        log.warning("rembg falló para %s: %s", image_url[:60], e)
        return None


def upload_transparent(s3, png_bytes: bytes, slug: str, sku: str) -> str:
    key_base = slug.strip() if slug and slug.strip() else sku.lower().strip()
    cdn_key = f"bigotesypaticas/products/{key_base}/transparent.png"
    s3.put_object(
        Bucket=CDN_BUCKET,
        Key=cdn_key,
        Body=png_bytes,
        ACL="public-read",
        ContentType="image/png",
        CacheControl="public, max-age=31536000",
    )
    return f"{CDN_BASE}/{cdn_key}"


def main():
    dry_run = "--dry" in sys.argv

    if not DB_URL:
        print("❌ DATABASE_URL_SYNC no configurada", file=sys.stderr)
        sys.exit(1)

    token = os.environ.get("REPLICATE_API_TOKEN", "")
    if not token:
        print("❌ REPLICATE_API_TOKEN no configurada", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(DB_URL, connect_timeout=10)
    cur = conn.cursor()

    # Productos con foto pero sin transparente
    cur.execute("""
        SELECT id::text, sku, slug, name, primary_image_url
        FROM catalog.products
        WHERE is_active = true
          AND primary_image_url IS NOT NULL
          AND primary_image_url != ''
          AND image_url_transparent IS NULL
        ORDER BY sku
    """)
    cols = [d[0] for d in cur.description]
    products = [dict(zip(cols, row)) for row in cur.fetchall()]

    log.info("Productos a procesar con rembg: %d", len(products))
    log.info("Costo estimado: $%.2f USD", len(products) * COST_PER_IMAGE)

    if dry_run:
        log.info("[DRY RUN] Sin --dry: procesaría %d productos", len(products))
        conn.close()
        return

    if not products:
        log.info("✅ Todos los productos ya tienen imagen transparente")
        conn.close()
        return

    rc = replicate.Client(api_token=token)
    s3 = s3_client()

    success = failed = 0
    total_cost = 0.0
    start = time.time()

    for i, p in enumerate(products, 1):
        sku  = p["sku"]
        slug = p["slug"] or ""
        img_url = p["primary_image_url"]

        png_bytes = remove_background(rc, img_url)
        if not png_bytes:
            failed += 1
            log.warning("[%d/%d] ✗ %s — rembg falló", i, len(products), sku[:30])
            continue

        try:
            cdn_url = upload_transparent(s3, png_bytes, slug, sku)
            now = datetime.utcnow().isoformat()
            cur.execute(
                """UPDATE catalog.products
                   SET image_url_transparent = %s, image_processed_at = %s, updated_at = NOW()
                   WHERE id = %s::uuid""",
                (cdn_url, now, p["id"]),
            )
            conn.commit()
            success += 1
            total_cost += COST_PER_IMAGE
            log.info("[%d/%d] ✓ %s → transparent.png", i, len(products), sku[:30])
        except Exception as e:
            log.error("[%d/%d] ✗ %s: %s", i, len(products), sku, e)
            conn.rollback()
            failed += 1

        if i % 25 == 0:
            elapsed = time.time() - start
            rate = i / elapsed * 60
            log.info(
                "--- Progreso: %d/%d OK | %d fallidos | $%.2f USD | %.1f imgs/min ---",
                success, len(products), failed, total_cost, rate,
            )
            # Pausa breve para no saturar Replicate
            time.sleep(1)

    conn.close()
    elapsed = time.time() - start
    log.info("=== REMBG COMPLETADO ===")
    log.info("Procesados: %d / %d", success, len(products))
    log.info("Fallidos: %d", failed)
    log.info("Costo total: $%.2f USD", total_cost)
    log.info("Tiempo: %.1f min", elapsed / 60)


if __name__ == "__main__":
    main()
