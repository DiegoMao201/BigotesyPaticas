"""Generador de Stories de solo texto sobre fondo de color — sin IA de imágenes.

100% gratis (Pillow, sin costo de API). Pensado para cuando no hay presupuesto
para generar imágenes con GPT-image-1 / Flux, pero igual se quiere publicar
contenido visual (Instagram Stories no acepta texto puro sin imagen de fondo).
"""

from __future__ import annotations

import random
import re
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
LOGO_PATH = Path("/app/apps/store/public/icon-192.png")
TEMP_DIR = Path("/tmp/content_engine")

# Paletas de marca — mismos colores usados en store/portal.
PALETTES: dict[str, dict[str, tuple[int, int, int]]] = {
    "teal": {"top": (13, 74, 69), "bottom": (24, 127, 119), "accent": (245, 166, 65)},
    "coral": {"top": (13, 74, 69), "bottom": (232, 67, 58), "accent": (255, 255, 255)},
    "gold": {"top": (24, 127, 119), "bottom": (245, 166, 65), "accent": (13, 74, 69)},
}

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF"
    "️"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text: str) -> str:
    """DejaVu Sans no tiene glifos de emoji (salen como tofu/cuadro) — se quitan
    del texto que se dibuja sobre la imagen. El caption real (aparte) sí puede
    llevar emojis normalmente."""
    return _EMOJI_RE.sub("", text).strip()


def _vertical_gradient(size: tuple[int, int], top_rgb, bottom_rgb) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, top_rgb)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        r = int(top_rgb[0] + (bottom_rgb[0] - top_rgb[0]) * t)
        g = int(top_rgb[1] + (bottom_rgb[1] - top_rgb[1]) * t)
        b = int(top_rgb[2] + (bottom_rgb[2] - top_rgb[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def generate_text_story(
    main_text: str,
    subtext: str = "BIGOTES Y PATICAS",
    footer: str = "bigotesypaticas.com",
    palette: str = "teal",
) -> Path:
    """Genera un PNG 1080x1920 (formato Story) con texto centrado sobre fondo
    degradado de marca. Devuelve el path local del archivo generado."""
    if palette not in PALETTES:
        palette = "teal"
    pal = PALETTES[palette]

    main_text = _strip_emoji(main_text)
    subtext = _strip_emoji(subtext)
    footer = _strip_emoji(footer)

    img = _vertical_gradient((W, H), pal["top"], pal["bottom"]).convert("RGBA")

    # Textura sutil de puntos translúcidos — sin assets externos.
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    rnd = random.Random(7)
    for _ in range(40):
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        r = rnd.randint(2, 5)
        odraw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 18))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Zona segura de IG Stories: evitar ~250px arriba (usuario/hora) y abajo (reply bar).
    safe_top, safe_bottom = 420, H - 420
    max_text_width = W - 160

    main_font = ImageFont.truetype(FONT_BOLD, 78)
    lines = _wrap_text(draw, main_text, main_font, max_text_width)
    line_height = main_font.size + 18
    block_height = line_height * len(lines)
    start_y = safe_top + (safe_bottom - safe_top - block_height) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=main_font)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        y = start_y + i * line_height
        draw.text((x + 3, y + 3), line, font=main_font, fill=(0, 0, 0, 90))
        draw.text((x, y), line, font=main_font, fill=(255, 255, 255, 255))

    if subtext:
        sub_font = ImageFont.truetype(FONT_BOLD, 40)
        bbox = draw.textbbox((0, 0), subtext, font=sub_font)
        sw = bbox[2] - bbox[0]
        sub_y = start_y + block_height + 50
        draw.text(((W - sw) // 2, sub_y), subtext, font=sub_font, fill=pal["accent"])

    if footer:
        foot_font = ImageFont.truetype(FONT_REG, 34)
        bbox = draw.textbbox((0, 0), footer, font=foot_font)
        fw = bbox[2] - bbox[0]
        draw.text(((W - fw) // 2, H - 360), footer, font=foot_font, fill=(255, 255, 255, 230))

    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo_size = 96
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        img.paste(logo, ((W - logo_size) // 2, H - 300), logo)

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = TEMP_DIR / f"story_{uuid.uuid4()}.png"
    img.convert("RGB").save(out_path, "PNG", optimize=True)
    return out_path
