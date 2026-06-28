"""Motor de generación de contenido IA — Sprint 6A.

Usa:
  - Claude Haiku 4.5 vía OpenRouter para rellenar templates y generar captions
  - GPT-image-1 (OpenAI) o Flux 1.1 Pro (Replicate) para generar imágenes
  - DO Spaces CDN para almacenamiento
  - Pillow para logo overlay (8% ancho, 60% opacidad, esquina inferior-derecha)
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import random
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import requests

log = logging.getLogger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────────

CDN_BASE    = os.environ.get("S3_PUBLIC_URL", "https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com")
CDN_BUCKET  = os.environ.get("S3_BUCKET", "catalogo-ferreinox")
CDN_ENDPOINT= os.environ.get("S3_ENDPOINT_URL", "https://nyc3.digitaloceanspaces.com")
CDN_REGION  = os.environ.get("S3_REGION", "nyc3")
S3_ACCESS   = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET   = os.environ.get("S3_SECRET_KEY", "")

LOGO_PATH   = Path("/app/apps/store/public/icon-192.png")
TEMP_DIR    = Path("/tmp/content_engine")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

BRAND_HASHTAGS = ["#BigotesYPaticasPereira", "#BigotesYPaticasDosquebradas"]

IMAGE_COSTS = {
    "gpt-image-1":  0.50,
    "flux-1.1-pro": 0.04,
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _openai_client():
    from openai import OpenAI
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY no configurada en environment")
    return OpenAI(api_key=key)


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


# ─── ContentGenerator ─────────────────────────────────────────────────────────

class ContentGenerator:
    """Genera posts completos: caption + imagen + upload CDN."""

    def __init__(self):
        self._openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not self._openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY no configurada en environment")
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # ── API pública ────────────────────────────────────────────────────────────

    async def generate_post(
        self,
        template: dict,
        context: dict,
        image_model: str = "gpt-image-1",
    ) -> dict:
        """Genera un post completo y lo devuelve listo para insertar en DB."""
        # Pre-sustituir hashtag rotativo antes de enviar a Claude
        brand_hashtag = random.choice(BRAND_HASHTAGS)
        tpl = dict(template)
        tpl["caption_template"] = tpl.get("caption_template", "").replace(
            "{brand_hashtag_rotating}", brand_hashtag
        )
        tpl["visual_prompt_template"] = tpl.get("visual_prompt_template", "").replace(
            "{brand_hashtag_rotating}", brand_hashtag
        )

        # 1. Claude Haiku rellena las variables del template
        filled = await asyncio.get_event_loop().run_in_executor(
            None, self._fill_template_with_claude, tpl, context
        )

        # 2. Generar imagen según modelo configurado
        cdn_url = None
        branded_path = None
        cost = IMAGE_COSTS.get(image_model, 0.50)
        try:
            if image_model == "flux-1.1-pro":
                raw_path = await asyncio.get_event_loop().run_in_executor(
                    None, self._generate_image_flux_pro, filled["visual_prompt"]
                )
            else:
                raw_path = await asyncio.get_event_loop().run_in_executor(
                    None, self._generate_image_gpt, filled["visual_prompt"]
                )
            branded_path = await asyncio.get_event_loop().run_in_executor(
                None, self._apply_logo_overlay, raw_path
            )
            cdn_url = await asyncio.get_event_loop().run_in_executor(
                None, self._upload_to_cdn, branded_path
            )
        except Exception as e:
            log.warning("Imagen no generada (se puede agregar manualmente): %s", e)
            cost = 0.0

        return {
            "visual_prompt":    filled["visual_prompt"],
            "caption":          filled["caption"],
            "hashtags":         filled.get("hashtags", []),
            "cta_url":          filled.get("cta_url"),
            "image_url":        cdn_url,
            "image_local_path": str(branded_path) if branded_path else None,
            "image_model":      image_model,
            "image_cost_usd":   cost,
        }

    async def regenerate_image(self, visual_prompt: str, image_model: str = "gpt-image-1") -> tuple[str, str, float]:
        """Regenera solo la imagen. Retorna (cdn_url, local_path, cost_usd)."""
        if image_model == "flux-1.1-pro":
            raw_path = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_image_flux_pro, visual_prompt
            )
            cost = IMAGE_COSTS["flux-1.1-pro"]
        else:
            raw_path = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_image_gpt, visual_prompt
            )
            cost = IMAGE_COSTS["gpt-image-1"]

        branded_path = await asyncio.get_event_loop().run_in_executor(
            None, self._apply_logo_overlay, raw_path
        )
        cdn_url = await asyncio.get_event_loop().run_in_executor(
            None, self._upload_to_cdn, branded_path
        )
        return cdn_url, str(branded_path), cost

    async def regenerate_image_with_model(
        self, visual_prompt: str, image_model: str
    ) -> tuple[str, str, float]:
        """Alias explícito para test A/B — genera con modelo alternativo."""
        return await self.regenerate_image(visual_prompt, image_model)

    # ── Paso 1: Claude Haiku rellena template ─────────────────────────────────

    def _fill_template_with_claude(self, template: dict, context: dict) -> dict:
        prompt = f"""Sos copywriter editorial de marca para Bigotes y Paticas, tienda premium de mascotas en Pereira/Dosquebradas Colombia.

ADN DE MARCA: conciencia animal, amor real, esperanza, autoridad técnica, identidad regional Pereira/Eje Cafetero. NO clichés genéricos.

Vas a generar contenido para post categoría "{template['category']}" usando este template:

VISUAL PROMPT TEMPLATE:
{template['visual_prompt_template']}

CAPTION TEMPLATE:
{template['caption_template']}

CONTEXTO ESPECÍFICO DEL POST:
{json.dumps(context, ensure_ascii=False, indent=2)}

INSTRUCCIONES CRÍTICAS:
1. Variables {{como_esta}}: rellenalas con datos ESPECÍFICOS y CREATIVOS, no genéricos.
2. Datos numéricos: cifras reales investigables (animales sin hogar Risaralda, % esterilización Pereira, etc).
3. Tono: adulto, técnico cuando aplica, empático. NUNCA cursi.
4. Caption máximo 250 palabras.
5. Hashtags: 5-7 que combinen marca + tema + local.
6. Para "awareness/adoption": datos verificables o "estimaciones aproximadas" honesto.
7. Para "product": beneficio ESPECÍFICO, no "es premium".
8. Para "educational": dato que el 80% de dueños NO sabe.
9. PROHIBIDO: "tu mejor amigo", "cuida tu mascota", "premium calidad", "amor incondicional".
10. CTAs siempre apuntan a bigotesypaticas.com o mi.bigotesypaticas.com o WhatsApp. NO tienda física como CTA principal.
11. Domicilio: GRATIS en pedidos +$30.000. Solo $5.000 en pedidos menores.

Respondé JSON estricto sin markdown:
{{"visual_prompt": "...", "caption": "...", "hashtags": ["#..."], "cta_url": "..." }}"""

        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {self._openrouter_key}",
                "HTTP-Referer": "https://bigotesypaticas.com",
                "X-Title": "Bigotes y Paticas Content Engine",
            },
            json={
                "model": "anthropic/claude-haiku-4-5",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.8,
            },
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            if "```" in raw:
                raw = raw.rsplit("```", 1)[0]
        return json.loads(raw.strip())

    # ── Paso 2a: GPT-image-1 ─────────────────────────────────────────────────

    def _generate_image_gpt(self, visual_prompt: str) -> Path:
        client = _openai_client()
        response = client.images.generate(
            model="gpt-image-1",
            prompt=visual_prompt,
            size="1024x1024",
            quality="high",
            n=1,
        )
        b64 = response.data[0].b64_json
        image_bytes = base64.b64decode(b64)

        out = TEMP_DIR / f"post_{uuid.uuid4()}.png"
        out.write_bytes(image_bytes)
        log.info("Imagen GPT-image-1 guardada: %s", out)
        return out

    # ── Paso 2b: Flux 1.1 Pro vía Replicate ──────────────────────────────────

    def _generate_image_flux_pro(self, visual_prompt: str) -> Path:
        """Genera imagen con Flux 1.1 Pro vía Replicate. Costo real ~$0.04/img."""
        import replicate

        token = os.environ.get("REPLICATE_API_TOKEN", "")
        if not token:
            raise RuntimeError("REPLICATE_API_TOKEN no configurada en environment")

        client = replicate.Client(api_token=token)
        output = client.run(
            "black-forest-labs/flux-1.1-pro",
            input={
                "prompt": visual_prompt,
                "aspect_ratio": "1:1",
                "output_format": "webp",
                "output_quality": 80,
                "safety_tolerance": 2,
                "prompt_upsampling": False,
            },
        )

        # output puede ser FileOutput, lista o URL string
        if isinstance(output, list):
            image_url = str(output[0])
        else:
            image_url = str(output)

        resp = requests.get(image_url, timeout=60)
        resp.raise_for_status()

        # Convertir webp → PNG con PIL
        from PIL import Image as PilImage
        img = PilImage.open(io.BytesIO(resp.content)).convert("RGB")
        out = TEMP_DIR / f"post_flux_{uuid.uuid4()}.png"
        img.save(out, "PNG")

        log.info("Imagen Flux 1.1 Pro guardada: %s (%.1f KB)", out, out.stat().st_size / 1024)
        return out

    # ── Paso 3: Logo overlay ──────────────────────────────────────────────────

    def _apply_logo_overlay(self, image_path: Path) -> Path:
        from PIL import Image

        img = Image.open(image_path).convert("RGBA")

        candidates = [
            LOGO_PATH,
            Path("/app/apps/store/public/icon-192.png"),
            Path("/app/icon-192.png"),
        ]
        logo_src = next((p for p in candidates if p.exists()), None)

        if logo_src:
            logo = Image.open(logo_src).convert("RGBA")
            logo_size = max(40, int(img.width * 0.08))
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
            r, g, b, a = logo.split()
            a = a.point(lambda p: int(p * 0.6))
            logo = Image.merge("RGBA", (r, g, b, a))
            padding = int(img.width * 0.03)
            pos = (img.width - logo.width - padding, img.height - logo.height - padding)
            img.paste(logo, pos, logo)
        else:
            log.warning("Logo no encontrado, se omite overlay")

        out = image_path.with_name(image_path.stem + "_branded.png")
        img.convert("RGB").save(out, "PNG", optimize=True)
        return out

    # ── Paso 4: Subida CDN ────────────────────────────────────────────────────

    def _upload_to_cdn(self, local_path: Path) -> str:
        s3 = _s3_client()
        date_path = datetime.now().strftime("%Y/%m/%d")
        dst_key = f"bigotesypaticas/content/{date_path}/{local_path.name}"

        s3.upload_file(
            str(local_path),
            CDN_BUCKET,
            dst_key,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": "image/png",
                "CacheControl": "public, max-age=2592000",
            },
        )
        url = f"{CDN_BASE}/{dst_key}"
        log.info("Imagen subida a CDN: %s", url)
        return url
