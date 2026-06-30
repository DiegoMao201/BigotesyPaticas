"""
Migrate products: remove 6-char hex hash suffix from slugs.

Usage:
  python scripts/migrate_clean_slugs.py --dry-run   # preview only
  python scripts/migrate_clean_slugs.py             # apply changes

Steps:
  1. Find products where slug ends in -[a-f0-9]{6}
  2. Compute clean_slug by stripping the hash
  3. If clean_slug is unique: update product, insert slug_redirect
  4. If collision: keep one clean, others get a suffix from their name
  5. Report stats
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from collections import defaultdict

import asyncpg

HASH_RE = re.compile(r"^(.+)-([a-f0-9]{6})$")
DB_URL = os.environ.get("DATABASE_URL", "")


def clean_slug(slug: str) -> str:
    m = HASH_RE.match(slug)
    if m:
        return m.group(1)
    return slug


def slugify_fragment(text: str) -> str:
    """Turn name fragment into a slug-safe string."""
    s = text.lower()
    s = re.sub(r"[áàäâ]", "a", s)
    s = re.sub(r"[éèëê]", "e", s)
    s = re.sub(r"[íìïî]", "i", s)
    s = re.sub(r"[óòöô]", "o", s)
    s = re.sub(r"[úùüû]", "u", s)
    s = re.sub(r"ñ", "n", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


async def run(dry_run: bool) -> None:
    if not DB_URL:
        print("ERROR: DATABASE_URL not set.", file=sys.stderr)
        sys.exit(1)

    conn = await asyncpg.connect(DB_URL)

    try:
        # Fetch all published products
        rows = await conn.fetch(
            "SELECT id, slug, name FROM catalog.products WHERE is_published = true"
        )
        print(f"Total productos publicados: {len(rows)}")

        # Separate hashed from clean
        hashed = [(r["id"], r["slug"], r["name"]) for r in rows if HASH_RE.match(r["slug"])]
        existing_slugs: set[str] = {r["slug"] for r in rows}

        print(f"Productos con hash: {len(hashed)}")

        # Build desired slug → list of (id, original_slug, name)
        desired: dict[str, list[tuple]] = defaultdict(list)
        for pid, slug, name in hashed:
            cs = clean_slug(slug)
            desired[cs].append((pid, slug, name))

        changes: list[tuple[str, str, str]] = []  # (product_id, old_slug, new_slug)
        collisions = 0

        for cs, candidates in desired.items():
            if len(candidates) == 1:
                pid, old_slug, name = candidates[0]
                # Check if clean slug is already taken by ANOTHER product
                target = cs
                if target in existing_slugs and target != old_slug:
                    # Add short fragment to disambiguate
                    words = name.split()[-2:]
                    fragment = slugify_fragment(" ".join(words))
                    target = f"{cs}-{fragment}"
                    collisions += 1
                changes.append((pid, old_slug, target))
            else:
                # Multiple products want the same clean slug
                collisions += len(candidates)
                for i, (pid, old_slug, name) in enumerate(candidates):
                    if i == 0:
                        target = cs  # first one gets the clean slug
                    else:
                        # Use last 2 words of name to disambiguate
                        words = name.split()[-2:]
                        fragment = slugify_fragment(" ".join(words))
                        target = f"{cs}-{fragment}"
                    changes.append((pid, old_slug, target))

        print(f"\nCambios a aplicar: {len(changes)}")
        print(f"Colisiones detectadas: {collisions}")
        print("\nPrimeros 30 cambios:")
        for _pid, old_s, new_s in changes[:30]:
            print(f"  {old_s}  →  {new_s}")

        if dry_run:
            print("\n[DRY RUN] No se aplicaron cambios.")
            return

        # Apply changes
        applied = 0
        redirects = 0
        async with conn.transaction():
            for pid, old_slug, new_slug in changes:
                if old_slug == new_slug:
                    continue
                await conn.execute(
                    "UPDATE catalog.products SET slug = $1 WHERE id = $2", new_slug, pid
                )
                # Insert redirect
                await conn.execute(
                    """
                    INSERT INTO catalog.slug_redirects (old_slug, new_slug, product_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (old_slug) DO UPDATE
                    SET new_slug = EXCLUDED.new_slug
                """,
                    old_slug,
                    new_slug,
                    pid,
                )
                applied += 1
                redirects += 1

        # Verify
        remaining = await conn.fetchval(
            "SELECT COUNT(*) FROM catalog.products WHERE slug ~ '-[a-f0-9]{6}$'"
        )
        total_redirects = await conn.fetchval("SELECT COUNT(*) FROM catalog.slug_redirects")

        print(f"\n✅ Cambios aplicados: {applied}")
        print(f"✅ Redirects creados: {redirects}")
        print(f"⚠️  Slugs con hash restantes: {remaining} (pueden ser hashes legítimos)")
        print(f"📊 Total en slug_redirects: {total_redirects}")

    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate product slugs — remove 6-char hash suffix"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not write")
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
