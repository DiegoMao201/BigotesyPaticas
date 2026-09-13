#!/usr/bin/env python3
"""Encuentra y lee el artículo real de una noticia.

Google News NO entrega el enlace verdadero (devuelve una página con JavaScript),
así que se busca el titular en DuckDuckGo, se prefiere el dominio del medio que
reportó la noticia y se extrae el texto del artículo.

Sin esto la IA solo tiene el titular y rellena con frases vacías.
"""
import re, urllib.parse
import requests

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"
BASURA = re.compile(r"suscr[ií]b|newsletter|cookies|pol[ií]tica de privacidad|todos los derechos|"
                    r"lea tambi[eé]n|le puede interesar|siga leyendo|compartir en|copyright|"
                    r"publicidad|whatsapp|telegram|s[ií]guenos", re.I)


def _sesion():
    s = requests.Session(); s.headers["User-Agent"] = UA
    return s


def _ddg(titulo, s):
    r = s.post("https://html.duckduckgo.com/html/", data={"q": titulo[:110]}, timeout=30)
    return [urllib.parse.unquote(u) for u in re.findall(r'uddg=([^&"]+)', r.text)]


def _bing(titulo, s):
    r = s.get("https://www.bing.com/search", params={"q": titulo[:110], "setlang": "es"}, timeout=30)
    return re.findall(r'<a[^>]+href="(https?://(?!www\.bing)[^"]+)"[^>]*>\s*<h2', r.text) or \
           re.findall(r'<h2><a[^>]+href="(https?://[^"]+)"', r.text)


def buscar_url(titulo, medio="", s=None):
    """URL real del artículo. DuckDuckGo bloquea consultas seguidas, así que se
    intenta también Bing antes de rendirse."""
    s = s or _sesion()
    urls = []
    for buscador in (_ddg, _bing):
        try:
            urls = [u for u in buscador(titulo, s) if u.startswith("http") and "duckduckgo" not in u]
        except Exception:
            urls = []
        if urls:
            break
    if not urls:
        return None
    clave = re.sub(r"[^a-z]", "", (medio or "").lower())[:8]
    if clave:
        for u in urls:
            if clave and clave[:6] in u.lower():
                return u
    return urls[0]


def leer(url, s=None, maximo=4000):
    """Extrae el texto del artículo. Devuelve '' si no consigue nada legible."""
    s = s or _sesion()
    try:
        r = s.get(url, timeout=30, allow_redirects=True)
        if r.status_code != 200:
            return ""
        html = r.text
    except Exception:
        return ""
    # el cuerpo suele estar en <p>; se descartan los párrafos de relleno
    html = re.sub(r"<(script|style|nav|footer|aside|form)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    parrafos = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.S | re.I)
    limpios = []
    for p in parrafos:
        t = re.sub(r"<[^>]+>", " ", p)
        t = re.sub(r"&nbsp;?", " ", t)
        t = re.sub(r"&[a-z]+;", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) < 60 or BASURA.search(t):
            continue
        limpios.append(t)
    texto = " ".join(limpios)
    return texto[:maximo]


def cuerpo(titulo, medio=""):
    """Atajo: busca y lee. Devuelve (url_real, texto)."""
    s = _sesion()
    u = buscar_url(titulo, medio, s)
    return (u, leer(u, s)) if u else (None, "")


if __name__ == "__main__":
    import sys
    u, t = cuerpo(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
    print("URL:", u)
    print("caracteres:", len(t))
    print(t[:700])
