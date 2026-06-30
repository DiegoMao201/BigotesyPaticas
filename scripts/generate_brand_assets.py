"""
Genera todos los assets de marca desde packages/branding/logo-source.png
Fuente: PNG cuadrado con fondo transparente (solo casita + perro + gato).
Requiere: pip install Pillow
"""

import base64
import shutil
from pathlib import Path

from PIL import Image

SOURCE = Path("packages/branding/logo-source.png")
assert SOURCE.exists(), f"NO ENCONTRADO: {SOURCE}"

src_img = Image.open(SOURCE).convert("RGBA")
print(f"Fuente: {SOURCE} ({src_img.size}, mode=RGBA)")

# Fondo teal para íconos que requieren fondo sólido (maskable / apple-touch)
TEAL_BG = (24, 127, 119, 255)


def render_png(size, output, bg=(0, 0, 0, 0), padding=1.0):
    """
    bg=(0,0,0,0): fondo transparente (íconos normales — logo flotante sobre cualquier fondo)
    bg=TEAL_BG: fondo sólido (apple-touch para iOS, maskable para PWA)
    padding=0.75: deja margen del 25% alrededor del logo (requerimiento maskable)
    """
    canvas = Image.new("RGBA", (size, size), bg)
    inner = int(size * padding)
    logo = src_img.copy()
    logo.thumbnail((inner, inner), Image.LANCZOS)
    offset = ((size - logo.width) // 2, (size - logo.height) // 2)
    canvas.paste(logo, offset, logo)

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, "PNG", optimize=True)
    kb = output.stat().st_size / 1024
    print(f"  ✓ {output} ({size}x{size}, {kb:.1f} KB)")


def render_ico(sizes, output):
    imgs = []
    for s in sizes:
        sq = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        logo = src_img.copy()
        logo.thumbnail((s, s), Image.LANCZOS)
        offset = ((s - logo.width) // 2, (s - logo.height) // 2)
        sq.paste(logo, offset, logo)
        imgs.append(sq)
    output.parent.mkdir(parents=True, exist_ok=True)
    imgs[0].save(output, format="ICO", sizes=[(s, s) for s in sizes], append_images=imgs[1:])
    print(f"  ✓ {output} (multi-size: {sizes})")


def render_opengraph(output):
    w, h = 1200, 630
    canvas = Image.new("RGB", (w, h), (13, 74, 69))
    pixels = canvas.load()
    for y in range(h):
        ratio = y / h
        r = int(13 + (24 - 13) * ratio)
        g = int(74 + (127 - 74) * ratio)
        b = int(69 + (119 - 69) * ratio)
        for x in range(w):
            pixels[x, y] = (r, g, b)
    logo = src_img.copy()
    logo.thumbnail((480, 480), Image.LANCZOS)
    x = (w - logo.width) // 2
    y = (h - logo.height) // 2
    canvas.paste(logo, (x, y), logo)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, "PNG", optimize=True)
    kb = output.stat().st_size / 1024
    print(f"  ✓ {output} (1200x630, {kb:.1f} KB)")


def create_svg_wrapper(output):
    with open(SOURCE, "rb") as f:
        png_b64 = base64.b64encode(f.read()).decode()
    w, h = src_img.size
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
        f'<image href="data:image/png;base64,{png_b64}" '
        f'width="{w}" height="{h}"/></svg>'
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg)
    print(f"  ✓ {output}")


# ── apps/store/public ──
store = Path("apps/store/public")
print(f"\n📁 {store}")
create_svg_wrapper(store / "icon.svg")
render_ico([16, 32, 48], store / "favicon.ico")
render_png(32, store / "icon-32.png")
render_png(192, store / "icon-192.png")
render_png(512, store / "icon-512.png")
render_png(180, store / "apple-touch-icon.png", bg=TEAL_BG, padding=0.80)
render_opengraph(store / "opengraph-image.png")

# ── apps/admin/public ──
admin = Path("apps/admin/public")
print(f"\n📁 {admin}")
create_svg_wrapper(admin / "icon.svg")
render_ico([16, 32, 48], admin / "favicon.ico")
render_png(32, admin / "icon-32.png")
render_png(192, admin / "icon-192.png")
render_png(512, admin / "icon-512.png")
render_png(180, admin / "apple-touch-icon.png", bg=TEAL_BG, padding=0.80)

# ── apps/portal/public ──
portal = Path("apps/portal/public")
print(f"\n📁 {portal}")
create_svg_wrapper(portal / "icon.svg")
render_ico([16, 32, 48], portal / "favicon.ico")
render_png(32, portal / "icon-32.png")
render_png(192, portal / "icon-192.png")
render_png(512, portal / "icon-512.png")
render_png(180, portal / "apple-touch-icon.png", bg=TEAL_BG, padding=0.80)
render_png(192, portal / "icon-maskable-192.png", bg=TEAL_BG, padding=0.75)
render_png(512, portal / "icon-maskable-512.png", bg=TEAL_BG, padding=0.75)

# ── dist/brand/cdn-uploads ──
cdn = Path("dist/brand/cdn-uploads")
print(f"\n📁 {cdn}")
create_svg_wrapper(cdn / "logo.svg")
shutil.copy2(SOURCE, cdn / "logo-original-1254.png")
render_png(256, cdn / "logo-256.png")
render_png(512, cdn / "logo-512.png")
render_png(1024, cdn / "logo-1024.png")

print("\n✅ Generación completa.")
