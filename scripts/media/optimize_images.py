"""
Optimiza imágenes: convierte a WebP con calidad configurable y genera variantes
responsive (thumb/card/main/zoom). Idempotente: omite si destino existe y es más nuevo.

Uso:
    python scripts/media/optimize_images.py --src local-assets/originals --dst local-assets/optimized
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Falta Pillow. Instalar:  pip install Pillow", file=sys.stderr)
    raise

VARIANTS = {
    "thumb": 200,
    "card": 600,
    "main": 1200,
    "zoom": 1600,
}
VALID_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def slugify_check(name: str) -> bool:
    return name == name.lower() and " " not in name and name.isascii()


def optimize_one(src: Path, dst_dir: Path, quality: int = 82) -> list[Path]:
    img = Image.open(src)
    if img.mode in ("RGBA", "LA", "P"):
        # Mantener transparencia si la hay
        rgba = img.convert("RGBA")
    else:
        rgba = img.convert("RGB")

    base = src.stem
    out: list[Path] = []
    for variant, max_side in VARIANTS.items():
        target = dst_dir / f"{base}-{variant}.webp"
        if target.exists() and target.stat().st_mtime >= src.stat().st_mtime:
            continue
        w, h = rgba.size
        scale = min(1.0, max_side / max(w, h))
        new_size = (round(w * scale), round(h * scale))
        resized = rgba.resize(new_size, Image.LANCZOS) if scale < 1.0 else rgba
        target.parent.mkdir(parents=True, exist_ok=True)
        save_mode = resized.mode
        if save_mode == "RGBA":
            resized.save(target, "WEBP", quality=quality, method=6)
        else:
            resized.save(target, "WEBP", quality=quality, method=6)
        out.append(target)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True, type=Path)
    p.add_argument("--dst", required=True, type=Path)
    p.add_argument("--quality", type=int, default=82)
    p.add_argument("--strict-naming", action="store_true",
                   help="Falla si encuentra archivos con nombres no conformes")
    args = p.parse_args()

    if not args.src.exists():
        print(f"src no existe: {args.src}", file=sys.stderr)
        return 1

    total = 0
    bad_names: list[Path] = []
    for src_file in args.src.rglob("*"):
        if not src_file.is_file() or src_file.suffix.lower() not in VALID_EXTS:
            continue
        if not slugify_check(src_file.name):
            bad_names.append(src_file)
            if args.strict_naming:
                continue
        rel = src_file.relative_to(args.src).parent
        dst_dir = args.dst / rel
        outputs = optimize_one(src_file, dst_dir, args.quality)
        for o in outputs:
            print(f"+ {o}")
            total += 1

    if bad_names:
        print("\nArchivos con naming no conforme (ver docs/IMAGE_NAMING_GUIDE.md):", file=sys.stderr)
        for b in bad_names:
            print(f"  - {b}", file=sys.stderr)
        if args.strict_naming:
            return 2

    print(f"\nGeneradas {total} variantes en {args.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
