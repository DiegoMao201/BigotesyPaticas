#!/usr/bin/env python3
"""Generador de Stories — Modo A (IA) — Bigotes y Paticas Sprint Stories.

Genera imagen vertical 9:16 con GPT-image-1, la combina con audio CC0
vía ffmpeg y sube el MP4 resultante al CDN.

Uso:
  docker exec <api> python3 scripts/generate_story.py --template tip_local_pereira
  docker exec <api> python3 scripts/generate_story.py --template producto_destacado_dia
  docker exec <api> python3 scripts/generate_story.py --scheduled "2026-06-30 10:00:00"
"""

from __future__ import annotations

import argparse
import asyncio
import io
import logging
import os
import random
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, "/app")

try:
    import psycopg2
except ModuleNotFoundError:
    import psycopg as psycopg2

import boto3
import requests
from botocore.client import Config
from PIL import Image

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

_BOGOTA = ZoneInfo("America/Bogota")

CDN_BUCKET = os.environ.get("S3_BUCKET", "catalogo-ferreinox")
CDN_ENDPOINT = os.environ.get("S3_ENDPOINT_URL", "https://nyc3.digitaloceanspaces.com")
CDN_REGION = os.environ.get("S3_REGION", "nyc3")
CDN_BASE = os.environ.get(
    "S3_PUBLIC_URL", "https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com"
)
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
DB_URL = (
    os.environ.get("DATABASE_URL_SYNC", "")
    .replace("postgresql+asyncpg://", "postgresql://")
    .replace("postgresql+psycopg://", "postgresql://")
)

AUDIO_CDN_BASE = f"{CDN_BASE}/bigotesypaticas/audio"
STORY_DURATION = 7  # segundos del video final

# Contextos educativos y tips para templates sin producto/reseña
_TIPS = [
    "El calor del Eje Cafetero acelera la deshidratación en mascotas — asegura agua fresca todo el día.",
    "Los perros en climas templados como Pereira necesitan baño cada 3-4 semanas para evitar hongos.",
    "Una dieta balanceada puede extender la vida de tu gato hasta 5 años más según estudios veterinarios.",
    "El 38% de los perros en Colombia tiene sobrepeso — controla las porciones con ayuda de tu veterinario.",
    "Las vacunas anuales son obligatorias por ley en Colombia — agenda la tuya antes de que venza.",
    "Los gatos necesitan al menos 12 horas de sueño — un ambiente tranquilo es esencial para su salud.",
]
_STATS = [
    {
        "number": "38%",
        "context": "de los perros en Colombia presentan sobrepeso según estudios nutricionales",
    },
    {
        "number": "72h",
        "context": "es el tiempo máximo sin agua que tolera un gato antes de sufrir daño renal",
    },
    {
        "number": "80%",
        "context": "de perros mayores de 3 años tienen algún grado de enfermedad periodontal",
    },
    {
        "number": "1 de 4",
        "context": "gatos domésticos en Colombia desarrolla cálculos urinarios por dieta seca",
    },
]


def s3_client():
    return boto3.client(
        "s3",
        region_name=CDN_REGION,
        endpoint_url=CDN_ENDPOINT,
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", ""),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", ""),
        config=Config(signature_version="s3v4"),
    )


def generate_image_gpt(prompt: str, tmp_dir: Path) -> Path:
    """Genera imagen 1024x1792 (9:16) con GPT-image-1."""
    import openai

    client = openai.OpenAI(api_key=OPENAI_KEY)
    resp = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1536",  # closest 9:16 soportado; ffmpeg escala a 1080x1920
        quality="medium",
        n=1,
    )
    import base64

    img_b64 = resp.data[0].b64_json
    img_bytes = base64.b64decode(img_b64)
    out = tmp_dir / "base_image.png"
    out.write_bytes(img_bytes)
    return out


def composite_product(base_img_path: Path, product_url: str, tmp_dir: Path) -> Path:
    """Superpone producto transparente sobre imagen base (centrado, ~45% del ancho)."""
    base = Image.open(base_img_path).convert("RGBA")
    resp = requests.get(product_url, timeout=30)
    resp.raise_for_status()
    prod = Image.open(io.BytesIO(resp.content)).convert("RGBA")

    # Redimensionar producto a 45% del ancho de la story
    target_w = int(base.width * 0.45)
    ratio = target_w / prod.width
    target_h = int(prod.height * ratio)
    prod = prod.resize((target_w, target_h), Image.LANCZOS)

    # Centrar horizontalmente, 35% desde arriba (zona media de la story)
    x = (base.width - target_w) // 2
    y = int(base.height * 0.35)
    base.paste(prod, (x, y), prod)

    out = tmp_dir / "composited.png"
    base.convert("RGB").save(out, "PNG")
    return out


def download_audio(genre: str, tmp_dir: Path) -> Path:
    """Descarga audio del CDN o usa silencio si falla."""
    audio_url = f"{AUDIO_CDN_BASE}/{genre}.mp3"
    out = tmp_dir / f"audio_{genre}.mp3"
    try:
        r = requests.get(audio_url, timeout=20)
        r.raise_for_status()
        out.write_bytes(r.content)
        return out
    except Exception as e:
        log.warning("Audio no disponible (%s): %s — generando silencio", genre, e)
        # Generar 7s de silencio con ffmpeg
        silence = tmp_dir / "silence.mp3"
        subprocess.run(
            [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=stereo",
                "-t",
                str(STORY_DURATION),
                "-q:a",
                "9",
                "-acodec",
                "libmp3lame",
                str(silence),
                "-y",
            ],
            check=True,
            capture_output=True,
        )
        return silence


def image_to_video(img_path: Path, audio_path: Path, duration: int, tmp_dir: Path) -> Path:
    """Convierte imagen + audio a MP4 H.264 9:16 con ffmpeg."""
    out = tmp_dir / "story.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(img_path),
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-t",
        str(duration),
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg falló: {result.stderr[-500:]}")
    return out


def upload_video(s3, video_path: Path, story_id: str) -> str:
    cdn_key = f"bigotesypaticas/stories/{story_id}.mp4"
    s3.upload_file(
        str(video_path),
        CDN_BUCKET,
        cdn_key,
        ExtraArgs={
            "ACL": "public-read",
            "ContentType": "video/mp4",
            "CacheControl": "public, max-age=86400",
        },
    )
    return f"{CDN_BASE}/{cdn_key}"


def build_context(template: dict, conn) -> dict:
    """Construye contexto según lo que requiere el template."""
    cur = conn.cursor()
    ctx: dict = {}

    if template["requires_real_product"]:
        cur.execute("""
            SELECT p.id::text, p.name, p.slug, p.price,
                   COALESCE(p.image_url_transparent, p.primary_image_url) as img
            FROM catalog.products p
            WHERE p.is_active=true AND p.is_published=true
              AND p.primary_image_url IS NOT NULL
            ORDER BY (p.image_url_transparent IS NOT NULL) DESC, RANDOM()
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            ctx.update(
                {
                    "product_id": row[0],
                    "product_name": row[1],
                    "product_slug": row[2],
                    "product_price": float(row[3] or 0),
                    "product_image_url": row[4],
                }
            )

    if template["requires_real_review"]:
        cur.execute("""
            SELECT r.comment, c.full_name
            FROM catalog.product_reviews r
            LEFT JOIN crm.customers c ON c.id = r.customer_id
            WHERE r.status IN ('approved','auto_published') AND r.rating >= 4
              AND r.comment IS NOT NULL AND LENGTH(r.comment) > 20
            ORDER BY RANDOM() LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            ctx.update(
                {"review_text": row[0][:120], "customer_name": (row[1] or "Cliente").split()[0]}
            )

    # Templates educativos
    if template["category"] == "educational":
        if "stat_number" in (template["visual_prompt_template"] or ""):
            s = random.choice(_STATS)
            ctx.update({"stat_number": s["number"], "stat_context": s["context"]})
        else:
            ctx["tip_message"] = random.choice(_TIPS)

    return ctx


def fill_prompt(template_text: str, ctx: dict) -> str:
    for k, v in ctx.items():
        template_text = template_text.replace("{" + k + "}", str(v))
    return template_text


async def generate_story(template_code: str, scheduled_at: str, conn, s3) -> str:
    """Genera una story completa y la guarda en DB. Retorna el story_post_id."""
    cur = conn.cursor()

    # Obtener template
    cur.execute(
        "SELECT * FROM content.story_templates WHERE code=%s AND active=true", (template_code,)
    )
    cols = [d[0] for d in cur.description]
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Template no encontrado: {template_code}")
    template = dict(zip(cols, row, strict=False))

    log.info("Generando story: %s → %s", template_code, scheduled_at)
    ctx = build_context(template, conn)

    story_id = str(uuid.uuid4())
    model = template["preferred_image_model"]
    cost = 0.0

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        # 1. Generar imagen base
        prompt = fill_prompt(template["visual_prompt_template"], ctx)
        if model == "gpt-image-1":
            img_path = generate_image_gpt(prompt, tmp_dir)
            cost = 0.04  # ~$0.04 por imagen medium 1024x1792
        else:
            # flux via Replicate
            import replicate

            rc = replicate.Client(api_token=os.environ.get("REPLICATE_API_TOKEN", ""))
            output = rc.run(
                "black-forest-labs/flux-1.1-pro",
                input={"prompt": prompt, "width": 1024, "height": 1792, "output_format": "png"},
            )
            img_url = str(output) if not isinstance(output, list) else str(output[0])
            r = requests.get(img_url, timeout=60)
            img_path = tmp_dir / "base_image.png"
            img_path.write_bytes(r.content)
            cost = 0.04

        # Subir imagen base al CDN
        base_key = f"bigotesypaticas/stories/base/{story_id}.png"
        s3.upload_file(
            str(img_path),
            CDN_BUCKET,
            base_key,
            ExtraArgs={"ACL": "public-read", "ContentType": "image/png"},
        )
        base_image_url = f"{CDN_BASE}/{base_key}"

        # 2. Composite producto si aplica
        if template["requires_real_product"] and ctx.get("product_image_url"):
            img_path = composite_product(img_path, ctx["product_image_url"], tmp_dir)

        # 3. Audio
        audio_path = download_audio(template["audio_genre"], tmp_dir)

        # 4. Imagen → Video MP4
        duration = template["audio_duration_sec"] or STORY_DURATION
        video_path = image_to_video(img_path, audio_path, duration, tmp_dir)

        video_size = video_path.stat().st_size
        log.info("Video generado: %s bytes", video_size)

        # 5. Subir video al CDN
        video_url = upload_video(s3, video_path, story_id)

    # 6. Caption
    caption = fill_prompt(template["caption_template"] or "", ctx)

    # 7. Swipe-up URL
    swipe_up = None
    dest = template.get("swipe_up_destination")
    if dest == "web":
        swipe_up = "https://www.bigotesypaticas.com"
    elif dest == "portal":
        swipe_up = "https://mi.bigotesypaticas.com"
    elif dest == "whatsapp":
        swipe_up = "https://wa.me/573206876633"
    elif dest == "product" and ctx.get("product_slug"):
        swipe_up = f"https://www.bigotesypaticas.com/products/{ctx['product_slug']}"

    # 8. Insertar en DB
    product_id = ctx.get("product_id")
    cur.execute(
        """
        INSERT INTO content.story_posts
          (id, template_code, creation_mode, media_type, video_url,
           video_duration_sec, video_size_bytes, video_resolution, video_has_audio,
           base_image_url, image_model, image_cost_usd,
           caption, swipe_up_url, product_id,
           status, dry_run, scheduled_at, expires_at,
           created_at, updated_at)
        VALUES
          (%s, %s, 'ai_generated', 'video', %s,
           %s, %s, '1080x1920', true,
           %s, %s, %s,
           %s, %s, %s::uuid,
           'pending_approval', false, %s, %s::timestamp + INTERVAL '24 hours',
           NOW(), NOW())
    """,
        (
            story_id,
            template_code,
            video_url,
            duration,
            video_size,
            base_image_url,
            model,
            cost,
            caption,
            swipe_up,
            product_id,
            scheduled_at,
            scheduled_at,
        ),
    )
    conn.commit()

    log.info("✓ Story creada: %s | video: %s | costo: $%.3f", story_id[:8], video_url[-40:], cost)
    return story_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default="tip_local_pereira")
    parser.add_argument("--scheduled", default=None, help="YYYY-MM-DD HH:MM:SS hora Colombia")
    parser.add_argument("--count", type=int, default=1, help="Generar N stories del mismo template")
    args = parser.parse_args()

    if not DB_URL:
        print("❌ DATABASE_URL_SYNC no configurada")
        sys.exit(1)
    if not OPENAI_KEY:
        print("❌ OPENAI_API_KEY no configurada")
        sys.exit(1)

    conn = psycopg2.connect(DB_URL, connect_timeout=10)
    s3 = s3_client()

    # Calcular scheduled_at si no se dio
    if args.scheduled:
        scheduled_at = args.scheduled
    else:
        now = datetime.now(_BOGOTA).replace(tzinfo=None)
        # Próximo slot disponible hoy (10am, 15pm, 19:30)
        slots = [(10, 0), (15, 0), (19, 30)]
        scheduled_at = None
        for h, m in slots:
            candidate = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if candidate > now:
                scheduled_at = candidate.strftime("%Y-%m-%d %H:%M:%S")
                break
        if not scheduled_at:
            tomorrow = now + timedelta(days=1)
            scheduled_at = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

    for i in range(args.count):
        log.info("Generando story %d/%d...", i + 1, args.count)
        story_id = asyncio.run(generate_story(args.template, scheduled_at, conn, s3))
        print(f"✅ Story {i+1}: {story_id}")

        # Ajustar scheduled_at para la siguiente si generamos varias
        if args.count > 1:
            dt = datetime.strptime(scheduled_at, "%Y-%m-%d %H:%M:%S")
            slots = [(10, 0), (15, 0), (19, 30)]
            next_slot = None
            for h, m in slots:
                candidate = dt.replace(hour=h, minute=m)
                if candidate > dt:
                    next_slot = candidate
                    break
            if not next_slot:
                next_slot = (dt + timedelta(days=1)).replace(
                    hour=10, minute=0, second=0, microsecond=0
                )
            scheduled_at = next_slot.strftime("%Y-%m-%d %H:%M:%S")

    conn.close()
    print(f"\n✅ {args.count} story(ies) en pending_approval → revisa en admin")


if __name__ == "__main__":
    main()
