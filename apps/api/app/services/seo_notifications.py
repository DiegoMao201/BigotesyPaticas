"""IndexNow — notificación instantánea a Bing/Yandex cuando cambia una URL."""
import os
from typing import Sequence
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
            await client.post(BING_URL, json=payload)
    except Exception as exc:  # noqa: BLE001
        print(f"[indexnow] Failed: {exc}")
