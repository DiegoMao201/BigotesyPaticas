#!/usr/bin/env python3
"""Sube fotos de productos desde Google Drive público al CDN.

Lógica idempotente:
- Cruza SKU del Drive (nombre de archivo sin ext) con catalog.products.sku
- SKIP productos que ya tienen primary_image_url en CDN
- Solo sube los que faltan (sin foto)
- Formato destino: bigotesypaticas/products/{slug}/main.png

Uso:
  docker exec <api> python scripts/sync_product_photos_from_drive.py
"""

from __future__ import annotations

import io
import logging
import os
import sys

sys.path.insert(0, "/app")

try:
    import psycopg2
except ModuleNotFoundError:
    import psycopg as psycopg2  # type: ignore[no-redef]

import boto3
import gdown
import requests
from botocore.client import Config
from PIL import Image

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/1RstDcCH6J54U_f4TT1-XovgtnAoq4wZW"

CDN_BUCKET = os.environ.get("S3_BUCKET", "catalogo-ferreinox")
CDN_ENDPOINT = os.environ.get("S3_ENDPOINT_URL", "https://nyc3.digitaloceanspaces.com")
CDN_REGION = os.environ.get("S3_REGION", "nyc3")
CDN_BASE = os.environ.get(
    "S3_PUBLIC_URL", "https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com"
)
S3_ACCESS = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET = os.environ.get("S3_SECRET_KEY", "")

DB_URL = (
    os.environ.get("DATABASE_URL_SYNC", "")
    .replace("postgresql+psycopg://", "postgresql://")
    .replace("postgresql+asyncpg://", "postgresql://")
)

MAX_SIDE = 1500  # px máximo por lado


def s3_client():
    return boto3.client(
        "s3",
        region_name=CDN_REGION,
        endpoint_url=CDN_ENDPOINT,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        config=Config(signature_version="s3v4"),
    )


def upload_image_to_cdn(
    s3, image_bytes: bytes, slug: str, sku: str, content_type: str = "image/png"
) -> str:
    key_base = slug.strip() if slug and slug.strip() else sku.lower().strip()
    cdn_key = f"bigotesypaticas/products/{key_base}/main.png"
    s3.put_object(
        Bucket=CDN_BUCKET,
        Key=cdn_key,
        Body=image_bytes,
        ACL="public-read",
        ContentType="image/png",
        CacheControl="public, max-age=31536000",
    )
    return f"{CDN_BASE}/{cdn_key}"


def download_from_drive(file_id: str) -> bytes | None:
    """Descarga archivo de Drive por ID (funciona con carpetas públicas)."""
    url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        log.warning("Error descargando %s: %s", file_id, e)
        return None


def process_image(raw_bytes: bytes) -> bytes:
    """Convierte a PNG, resize si >MAX_SIDE, preserva transparencia si tiene."""
    img = Image.open(io.BytesIO(raw_bytes))
    if img.mode not in ("RGBA", "LA"):
        img = img.convert("RGB")
    if img.width > MAX_SIDE or img.height > MAX_SIDE:
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def main():
    if not DB_URL:
        print("❌ DATABASE_URL_SYNC no configurada", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(DB_URL, connect_timeout=10)
    cur = conn.cursor()
    s3 = s3_client()

    # 1. Listar archivos en Drive
    log.info("Listando archivos en Drive (carpeta pública)...")
    drive_files = gdown.download_folder(url=DRIVE_FOLDER_URL, quiet=True, skip_download=True)
    drive_map: dict[str, str] = {}  # sku_lower → file_id
    for f in drive_files:
        name = f.path.split("/")[-1]
        base = name.rsplit(".", 1)[0].lower().strip()
        if base and base not in (
            "captura de pantalla 2026-06-28 183225",
            "captura de pantalla 2026-06-28 183351",
        ):
            drive_map[base] = f.id
    log.info("Drive: %d archivos válidos indexados", len(drive_map))

    # 2. Productos sin foto + que tienen SKU en Drive
    cur.execute("""
        SELECT id::text, sku, slug, name
        FROM catalog.products
        WHERE is_active = true
          AND (primary_image_url IS NULL OR primary_image_url = '')
    """)
    cols = [d[0] for d in cur.description]
    sin_foto = [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]

    to_upload = []
    for p in sin_foto:
        sku_key = (p["sku"] or "").lower().strip()
        if sku_key in drive_map:
            to_upload.append({**p, "drive_file_id": drive_map[sku_key]})

    log.info("Productos sin foto con match en Drive: %d", len(to_upload))

    # 3. Subir
    success = failed = 0
    for i, item in enumerate(to_upload, 1):
        sku = item["sku"]
        slug = item["slug"] or ""
        file_id = item["drive_file_id"]

        raw = download_from_drive(file_id)
        if not raw:
            log.warning("[%d/%d] ✗ %s — descarga fallida", i, len(to_upload), sku)
            failed += 1
            continue

        try:
            png_bytes = process_image(raw)
            cdn_url = upload_image_to_cdn(s3, png_bytes, slug, sku)

            cur.execute(
                "UPDATE catalog.products SET primary_image_url = %s, updated_at = NOW() WHERE id = %s::uuid",
                (cdn_url, item["id"]),
            )
            conn.commit()
            success += 1
            log.info("[%d/%d] ✓ %s → %s", i, len(to_upload), sku[:30], cdn_url.split("/")[-3])

        except Exception as e:
            log.error("[%d/%d] ✗ %s: %s", i, len(to_upload), sku, e)
            conn.rollback()
            failed += 1

        if i % 25 == 0:
            log.info("--- Progreso: %d OK / %d fallidos ---", success, failed)

    conn.close()
    log.info("=== SYNC COMPLETADO ===")
    log.info("Exitosos: %d / %d", success, len(to_upload))
    log.info("Fallidos: %d", failed)


if __name__ == "__main__":
    main()
