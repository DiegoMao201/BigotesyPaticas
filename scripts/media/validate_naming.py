"""
Validador de naming de assets (lee docs/IMAGE_NAMING_GUIDE.md como referencia humana,
aplica reglas en código).

Uso:
    python scripts/media/validate_naming.py local-assets/optimized
    # exit 0 si todo OK, 1 si hay violaciones
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

VALID_EXT = {".webp", ".png", ".svg", ".jpg", ".jpeg"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:[-/][a-z0-9]+)*$")


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(root).as_posix()
        if f.suffix.lower() not in VALID_EXT:
            errors.append(f"extensión inválida: {rel}")
            continue
        stem = f.stem
        if not stem.islower():
            errors.append(f"mayúsculas: {rel}")
        if " " in rel or not rel.isascii():
            errors.append(f"espacios o no-ASCII: {rel}")
        if not SLUG_RE.match(stem):
            errors.append(f"slug inválido (usar kebab-case): {rel}")
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1])
    if not root.exists():
        print(f"no existe: {root}", file=sys.stderr)
        return 2
    errors = validate(root)
    if errors:
        print("Violaciones de naming:")
        for e in errors:
            print(f"  ✗ {e}")
        return 1
    print(f"OK ({sum(1 for _ in root.rglob('*') if _.is_file())} archivos verificados)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
