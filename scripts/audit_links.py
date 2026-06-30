"""
Auditoría de links rotos en bigotesypaticas.com.
Correr: python scripts/audit_links.py [--prod]
"""

import asyncio
import sys
from urllib.parse import urljoin, urlparse

try:
    import httpx
    from bs4 import BeautifulSoup
except ImportError:
    print("Instalar: pip install httpx beautifulsoup4")
    sys.exit(1)

BASE = "https://bigotesypaticas.com" if "--prod" in sys.argv else "http://localhost:3000"


async def crawl_and_check():
    visited: set[str] = set()
    broken: list[tuple[str, str | int]] = []
    to_visit: list[str] = [BASE]

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        while to_visit and len(visited) < 500:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)

            try:
                r = await client.get(url)
                if r.status_code >= 400:
                    broken.append((url, r.status_code))
                    continue
                if "text/html" not in r.headers.get("content-type", ""):
                    continue

                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    link = urljoin(url, a["href"])
                    parsed = urlparse(link)
                    if (
                        "bigotesypaticas.com" in parsed.netloc
                        or parsed.netloc == ""
                        or "localhost" in parsed.netloc
                    ) and not link.startswith(("mailto:", "tel:", "#")):
                        # Exclude mailto, tel, anchors
                        norm = link.split("#")[0].rstrip("/")
                        if norm not in visited and norm not in to_visit:
                            to_visit.append(norm)
            except Exception as e:
                broken.append((url, str(e)))

    print(f"\n{'='*60}")
    print(f"AUDITORÍA DE LINKS — {BASE}")
    print(f"{'='*60}")
    print(f"✓ Visitadas: {len(visited)}")
    print(f"✗ Rotas: {len(broken)}\n")
    for url, status in broken:
        print(f"  ❌ {status}: {url}")

    if not broken:
        print("  ✅ Sin links rotos")

    return broken


if __name__ == "__main__":
    asyncio.run(crawl_and_check())
