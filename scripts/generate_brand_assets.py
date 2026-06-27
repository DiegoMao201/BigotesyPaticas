"""
Genera todos los assets de marca desde packages/branding/logo-source.svg
Requiere: pip install cairosvg Pillow
"""
import io
import shutil
from pathlib import Path

import cairosvg
from PIL import Image

SOURCE = Path("packages/branding/logo-source.svg")
assert SOURCE.exists(), f"NO ENCONTRADO: {SOURCE}"


def render_png(size, output, bg=None, maskable=False, canvas_size=None):
    if canvas_size:
        w, h = canvas_size
        canvas = Image.new("RGB", (w, h), (248, 249, 250))
        logo_h = int(h * 0.6)
        logo_w = logo_h
        logo_png = cairosvg.svg2png(
            url=str(SOURCE.resolve()),
            output_width=logo_w,
            output_height=logo_h,
        )
        logo_img = Image.open(io.BytesIO(logo_png)).convert("RGBA")
        x = (w - logo_w) // 2
        y = (h - logo_h) // 2
        canvas.paste(logo_img, (x, y), logo_img)
        img = canvas
    else:
        png_bytes = cairosvg.svg2png(
            url=str(SOURCE.resolve()),
            output_width=size,
            output_height=size,
        )
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")

        if maskable:
            padded = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            inner = int(size * 0.8)
            resized = img.resize((inner, inner), Image.LANCZOS)
            offset = (size - inner) // 2
            padded.paste(resized, (offset, offset), resized)
            img = padded

        if bg == "dark":
            bg_img = Image.new("RGBA", img.size, (13, 74, 69, 255))
            bg_img.paste(img, (0, 0), img)
            img = bg_img.convert("RGB")

    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output, "PNG", optimize=True)
    print(f"  ✓ {output} ({img.size[0]}x{img.size[1]})")


def render_ico(sizes, output):
    imgs = []
    for s in sizes:
        png = cairosvg.svg2png(url=str(SOURCE.resolve()), output_width=s, output_height=s)
        imgs.append(Image.open(io.BytesIO(png)).convert("RGBA"))
    output.parent.mkdir(parents=True, exist_ok=True)
    imgs[0].save(output, format="ICO", sizes=[(s, s) for s in sizes], append_images=imgs[1:])
    print(f"  ✓ {output} (sizes: {sizes})")


def copy_svg(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, output)
    print(f"  ✓ {output}")


# ── apps/store/public ──
store = Path("apps/store/public")
print(f"\n📁 {store}")
copy_svg(store / "icon.svg")
render_ico([16, 32, 48], store / "favicon.ico")
render_png(32, store / "icon-32.png")
render_png(192, store / "icon-192.png")
render_png(512, store / "icon-512.png")
render_png(180, store / "apple-touch-icon.png")
render_png(0, store / "opengraph-image.png", canvas_size=(1200, 630))

# ── apps/admin/public ──
admin = Path("apps/admin/public")
print(f"\n📁 {admin}")
copy_svg(admin / "icon.svg")
render_ico([16, 32, 48], admin / "favicon.ico")
render_png(32, admin / "icon-32.png")
render_png(192, admin / "icon-192.png")
render_png(512, admin / "icon-512.png")
render_png(180, admin / "apple-touch-icon.png")

# ── apps/portal/public ──
portal = Path("apps/portal/public")
print(f"\n📁 {portal}")
copy_svg(portal / "icon.svg")
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
copy_svg(cdn / "logo.svg")
render_png(256, cdn / "logo-256.png")
render_png(512, cdn / "logo-512.png")
render_png(1024, cdn / "logo-1024.png")
render_png(2048, cdn / "logo-2048.png")
render_png(2048, cdn / "logo-on-dark-2048.png", bg="dark")

print("\n✅ Generación completa")
print("\n📋 Archivos generados:")
for d in [store, admin, portal, cdn]:
    print(f"\n{d}:")
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix in (".png", ".ico", ".svg", ".webmanifest"):
            size_kb = f.stat().st_size / 1024
            print(f"  {f.name:40} {size_kb:8.2f} KB")
