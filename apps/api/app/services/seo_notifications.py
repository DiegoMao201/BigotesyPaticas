"""IndexNow — notificación instantánea a Bing/Yandex cuando cambia una URL."""

import os
from collections.abc import Sequence

import httpx

INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "")
HOST = "bigotesypaticas.com"
BING_URL = "https://www.bing.com/indexnow"


async def notify_indexnow(urls: Sequence[str]) -> None:
    if not INDEXNOW_KEY or not urls:
        return

    payload = {
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{HOST}/{INDEXNOW_KEY}.txt",
        "urlList": list(urls)[:10000],
    }

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.post(BING_URL, json=payload)
        # 24-oct-2026: antes no se miraba la respuesta; un 403 (llave rechazada) o un
        # 422 (URL de otro dominio) pasaban en silencio y nadie se enteraba.
        if r.status_code not in (200, 202):
            print(f"[indexnow] Bing respondió {r.status_code}: {r.text[:200]} ({len(payload['urlList'])} URLs)")
    except Exception as exc:
        print(f"[indexnow] Failed: {exc}")
