#!/usr/bin/env python3
"""
Envía batch de URLs críticas a IndexNow (Bing + Yandex) y pings del sitemap.
Uso: python scripts/seo_push.py

No requiere variables de entorno adicionales — la clave está en el dominio.
"""

import asyncio
import json

import httpx

SITE = "https://bigotesypaticas.com"
INDEXNOW_KEY = "7mimi866606do0F42do9b244mi6a62mi208374"
KEY_LOCATION = f"{SITE}/{INDEXNOW_KEY}.txt"

CRITICAL_URLS = [
    f"{SITE}/",
    f"{SITE}/categorias/perros",
    f"{SITE}/categorias/gatos",
    f"{SITE}/categorias/accesorios",
    f"{SITE}/categorias/snacks",
    f"{SITE}/categorias/todos",
    f"{SITE}/buscar",
    f"{SITE}/blog",
    f"{SITE}/contacto",
    f"{SITE}/devoluciones",
    f"{SITE}/checkout",
    f"{SITE}/carrito",
    # Landing pages SEO
    f"{SITE}/alimento-para-perros-pereira",
    f"{SITE}/alimento-para-gatos-pereira",
    f"{SITE}/accesorios-mascotas-pereira",
    f"{SITE}/veterinaria-domicilio-pereira",
    f"{SITE}/tienda-mascotas-dosquebradas",
    # Portal
    f"https://portal.bigotesypaticas.com/",
    f"https://portal.bigotesypaticas.com/login",
    # Sitemap
    f"{SITE}/sitemap.xml",
]

INDEXNOW_ENDPOINTS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
]

SITEMAP_PING_URL = f"https://www.bing.com/ping?sitemap={SITE}/sitemap.xml"


async def push_indexnow(client: httpx.AsyncClient, endpoint: str, urls: list[str]) -> bool:
    payload = {
        "host": "bigotesypaticas.com",
        "key": INDEXNOW_KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }
    try:
        r = await client.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=20,
        )
        if r.status_code in (200, 202):
            print(f"  ✅ {endpoint} → {r.status_code} ({len(urls)} URLs)")
            return True
        else:
            print(f"  ⚠️  {endpoint} → {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ {endpoint} → error: {e}")
        return False


async def ping_sitemap(client: httpx.AsyncClient) -> bool:
    try:
        r = await client.get(SITEMAP_PING_URL, timeout=15)
        print(f"  {'✅' if r.status_code == 200 else '⚠️ '} Sitemap ping → {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"  ❌ Sitemap ping → {e}")
        return False


async def main():
    # Solo URLs de la store (IndexNow no acepta subdominios distintos en un mismo batch)
    store_urls = [u for u in CRITICAL_URLS if "bigotesypaticas.com" in u and "portal." not in u]

    print(f"🚀 IndexNow — enviando {len(store_urls)} URLs críticas")
    print(json.dumps(store_urls, indent=2, ensure_ascii=False))
    print()

    async with httpx.AsyncClient() as client:
        for endpoint in INDEXNOW_ENDPOINTS:
            await push_indexnow(client, endpoint, store_urls)

        print("\n📡 Sitemap ping →")
        await ping_sitemap(client)

    print("\n✅ SEO push completado")


if __name__ == "__main__":
    asyncio.run(main())
