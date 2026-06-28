"""
Genera todos los assets de marca desde packages/branding/logo-source.png
Requiere: pip install Pillow
Fuente: PNG 2048x2048 RGBA con fondo transparente
"""
import base64
import shutil
from pathlib import Path

from PIL import Image

SOURCE = Path("packages/branding/logo-source.png")
assert SOURCE.exists(), f"NO ENCONTRADO: {SOURCE}"

src_img = Image.open(SOURCE).convert("RGBA")
assert src_img.mode == "RGBA", "La imagen fuente debe ser RGBA"


def _square_resize(size: int) -> Image.Image:
    """Redimensiona manteniendo aspect ratio, centra en lienzo cuadrado transparente."""
    img = src_img.copy()
    img.thumbnail((size, size), Image.LANCZOS)
    square = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    offset = ((size - img.width) // 2, (size - img.height) // 2)
    square.paste(img, offset, img)
    return square


def render_png(size, output, bg=None, maskable=False, canvas_size=None):
    if canvas_size:
        w, h = canvas_size
        canvas = Image.new("RGB", (w, h), (248, 249, 250))
        logo_h = int(h * 0.6)
        logo_img = src_img.copy()
        logo_img.thumbnail((logo_h, logo_h), Image.LANCZOS)
        x = (w - logo_img.width) // 2
        y = (h - logo_img.height) // 2
        canvas.paste(logo_img, (x, y), logo_img)
        img = canvas
    else:
        img = _square_resize(size)

        if maskable:
            padded = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            inner = int(size * 0.8)
            resized = _square_resize(inner)
            o = (size - inner) // 2
            padded.paste(resized, (o, o), resized)
            img = padded

        if bg == "dark":
            bg_img = Image.new("RGBA", img.size, (13, 74, 69, 255))
            bg_img.paste(img, (0, 0), img)
            img = bg_img.convert("RGB")

    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output, "PNG", optimize=True)
    print(f"  ✓ {output} ({img.size[0]}x{img.size[1]}, {img.mode})")


def render_ico(sizes, output):
    imgs = []
    for s in sizes:
        imgs.append(_square_resize(s))
    output.parent.mkdir(parents=True, exist_ok=True)
    imgs[0].save(output, format="ICO", sizes=[(s, s) for s in sizes], append_images=imgs[1:])
    print(f"  ✓ {output} (sizes: {sizes})")


def create_svg_wrapper(output):
    """SVG wrapper que embebe el PNG transparente como data URI."""
    with open(SOURCE, "rb") as f:
        png_b64 = base64.b64encode(f.read()).decode()
    w, h = src_img.size
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">\n  <image href="data:image/png;base64,{png_b64}" width="{w}" height="{h}"/>\n</svg>\n'
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
render_png(180, store / "apple-touch-icon.png")
render_png(0, store / "opengraph-image.png", canvas_size=(1200, 630))

# ── apps/admin/public ──
admin = Path("apps/admin/public")
print(f"\n📁 {admin}")
create_svg_wrapper(admin / "icon.svg")
render_ico([16, 32, 48], admin / "favicon.ico")
render_png(32, admin / "icon-32.png")
render_png(192, admin / "icon-192.png")
render_png(512, admin / "icon-512.png")
render_png(180, admin / "apple-touch-icon.png")

# ── apps/portal/public ──
portal = Path("apps/portal/public")
print(f"\n📁 {portal}")
create_svg_wrapper(portal / "icon.svg")
render_ico([16, 32, 48], portal / "favicon.ico")
render_png(32, portal / "icon-32.png")
render_png(192, portal / "icon-192.png")
render_png(512, portal / "icon-512.png")
render_png(180, portal / "apple-touch-icon.png")
render_png(192, portal / "icon-maskable-192.png", maskable=True)
render_png(512, portal / "icon-maskable-512.png", maskable=True)

# ── dist/brand/cdn-uploads ──
cdn = Path("dist/brand/cdn-uploads")
print(f"\n📁 {cdn}")
create_svg_wrapper(cdn / "logo.svg")
shutil.copy2(SOURCE, cdn / "logo-original.png")
render_png(256, cdn / "logo-256.png")
render_png(512, cdn / "logo-512.png")
render_png(1024, cdn / "logo-1024.png")
render_png(2048, cdn / "logo-2048.png")
render_png(2048, cdn / "logo-on-dark-2048.png", bg="dark")

print("\n✅ Generación completa")
print("\n📋 Resumen:")
for d in [store, admin, portal, cdn]:
    print(f"\n{d}:")
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix in (".png", ".ico", ".svg", ".webmanifest"):
            print(f"  {f.name:40} {f.stat().st_size/1024:7.1f} KB")
