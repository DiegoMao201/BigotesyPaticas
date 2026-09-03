"""Subida de imágenes a DigitalOcean Spaces (S3-compatible), convertidas a WebP.

Mismo Space/bucket que ya usa `content_generator.py` — se reutiliza para fotos
de usuarios (SOS, adopción, etc.) bajo un prefijo de key distinto.
"""

from __future__ import annotations

import io
import os
import uuid
from functools import lru_cache

CDN_BASE = os.environ.get(
    "S3_PUBLIC_URL", "https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com"
)
CDN_BUCKET = os.environ.get("S3_BUCKET", "catalogo-ferreinox")
CDN_ENDPOINT = os.environ.get("S3_ENDPOINT_URL", "https://nyc3.digitaloceanspaces.com")
CDN_REGION = os.environ.get("S3_REGION", "nyc3")
S3_ACCESS = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET = os.environ.get("S3_SECRET_KEY", "")

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


@lru_cache(maxsize=1)
def _s3_client():
    import boto3
    from botocore.client import Config

    return boto3.client(
        "s3",
        region_name=CDN_REGION,
        endpoint_url=CDN_ENDPOINT,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        config=Config(signature_version="s3v4"),
    )


def upload_image_webp(
    contents: bytes,
    key_prefix: str,
    *,
    max_size: tuple[int, int] = (1280, 1280),
    thumb_size: tuple[int, int] = (400, 400),
) -> dict[str, str]:
    """Convierte a WebP (imagen + thumbnail) y sube ambas al Space. Devuelve URLs públicas."""
    from PIL import Image, ImageOps

    # Las fotos de celular traen la rotación en EXIF; sin exif_transpose la
    # imagen se guarda acostada y así se ve en toda la web.
    img = Image.open(io.BytesIO(contents))
    img = ImageOps.exif_transpose(img) or img
    img = img.convert("RGB")

    main = img.copy()
    main.thumbnail(max_size, Image.LANCZOS)
    main_buf = io.BytesIO()
    main.save(main_buf, format="WEBP", quality=82, method=6)

    thumb = img.copy()
    thumb.thumbnail(thumb_size, Image.LANCZOS)
    thumb_buf = io.BytesIO()
    thumb.save(thumb_buf, format="WEBP", quality=75, method=6)

    file_id = uuid.uuid4().hex
    main_key = f"{key_prefix}/{file_id}.webp"
    thumb_key = f"{key_prefix}/{file_id}_thumb.webp"

    s3 = _s3_client()
    extra = {
        "ACL": "public-read",
        "ContentType": "image/webp",
        "CacheControl": "public, max-age=2592000",
    }
    s3.put_object(Bucket=CDN_BUCKET, Key=main_key, Body=main_buf.getvalue(), **extra)
    s3.put_object(Bucket=CDN_BUCKET, Key=thumb_key, Body=thumb_buf.getvalue(), **extra)

    return {"url": f"{CDN_BASE}/{main_key}", "thumb_url": f"{CDN_BASE}/{thumb_key}"}
