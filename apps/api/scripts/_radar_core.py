#!/usr/bin/env python3
"""Radar de noticias de perros y gatos para Bigotes y Paticas.

Lee noticias reales por RSS, descarta las repetidas, las puntúa por importancia
y deja las mejores listas para convertirse en video.

  radar_noticias.py                 # muestra el ranking de hoy (no toca nada)
  radar_noticias.py --json salida.json

Reglas que pidió Diego (12-sep-2026):
  - Solo noticias REALES de medios reconocibles. Informar, no desinformar.
  - Interés nacional: normas, leyes, derechos, deberes, estudios, nutrición.
    Lo puramente local de Bogotá NO entra salvo que aplique a todo el país.
  - Máximo 2 piezas por día, las de mayor puntaje.
  - Las viejas pero vigentes se cuentan como "¿Sabías que...?".
"""
import argparse, hashlib, json, re, sys, unicodedata, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

BOGOTA = timezone(timedelta(hours=-5))
GN = "https://news.google.com/rss/search?q={}&hl=es-419&gl=CO&ceid=CO:es-419"

CONSULTAS = [
    "ley OR norma OR decreto mascotas Colombia",
    "bienestar animal Colombia",
    "maltrato animal Colombia denuncia",
    "perros gatos derechos Colombia",
    "tenencia responsable mascotas Colombia",
    "estudio OR investigacion perros gatos comportamiento",
    "alimento OR nutricion perros gatos alerta",
    "vacunacion OR rabia OR esterilizacion mascotas Colombia",
    "mascotas Risaralda OR Pereira OR Dosquebradas",
]

# Medios reconocibles: el motor NO inventa, solo reproduce hechos de estas fuentes.
FUENTES = {
    "eltiempo": 10, "infobae": 9, "elespectador": 9, "semana": 8, "elcolombiano": 8,
    "rcn": 8, "caracol": 8, "bluradio": 7, "lafm": 7, "wradio": 7, "eluniversal": 7,
    "vanguardia": 7, "elpais": 7, "publimetro": 5, "lasillavacia": 7, "pulzo": 5,
    "minambiente.gov.co": 10, "policia.gov.co": 10, "ica.gov.co": 10,
    "minsalud.gov.co": 10, "bogota.gov.co": 6, "animalesbog.gov.co": 6,
}
# Palabras que suben el puntaje (lo que de verdad le sirve a un dueño)
PESOS = [
    (r"\bley\b|decreto|resoluci[oó]n|reglament|norma\b|sanci[oó]n|multa", 14),
    (r"obligatori|requisito|prohib|entra en vigencia|desde 20\d\d", 10),
    (r"derecho|deber|denunci|ruta de atenci|proteccion animal", 8),
    (r"estudio|investigaci[oó]n|cient[ií]fic|universidad|revista", 8),
    (r"alerta|riesgo|t[oó]xic|envenena|brote|rabia|retiro del mercado", 9),
    (r"esteriliza|vacuna|salud animal|veterinar", 6),
    (r"nutrici|alimento|concentrado|dieta", 6),
    (r"adopci[oó]n|rescate|refugio", 4),
]
NACIONAL = r"colombia|nacional|gobierno|congreso|ministerio|minambiente|todo el pa[ií]s"
LOCAL_NUESTRO = r"risaralda|pereira|dosquebradas|eje cafetero"
SOLO_BOGOTA = r"\bbogot[aá]\b|distrito|localidad|alcald[ií]a de bogot|idpyba|usaqu|suba\b|chapinero"
# Ruido a descartar de entrada
# Ruido y temas que NO le convienen a la marca (una tienda de mascotas no publica
# zoofilia, crímenes sexuales ni política de partidos, por muy noticia que sean).
VETO = (r"perro caliente|hot dog|gato hidr[aá]ulico|gato del carro|perros de la guerra|apuestas"
        r"|acceso carnal|zoofil|abuso sexual|violaci[oó]n|feminicidio|narco|guerrill"
        r"|amenazas de muerte|homicidio|secuestr"
        # Política y escándalos: reales, pero una tienda de mascotas no los publica.
        # Se coló "la veterinaria fantasma" (corrupción con Ecopetrol) solo porque
        # la empresa llevaba el nombre de los gatos del dueño.
        # Ojo: nada de vetar "senador" ni "contrato" a secas — la Ley Ángel la
        # autoró una senadora y quedó bloqueada. Solo palabras de escándalo.
        r"|ecopetrol|corrupci|peculado|licitaci[oó]n|contrato fantasma|empresa fantasma"
        r"|veterinaria fantasma|campa[nñ]a pol[ií]tica|candidato presidencial|imputan cargos")


def _norm(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


VACIAS = {"sobre", "contra", "desde", "hasta", "entre", "segun", "tienen", "podran",
          "deberan", "cuales", "estos", "estas", "puede", "pueden", "ahora", "nuevo",
          "nueva", "nuevos", "nuevas", "ademas", "tambien", "mientras", "asi"}


def _palabras(titulo):
    n = _norm(titulo).split(" - ")[0]
    return {w for w in re.findall(r"[a-z]{5,}", n) if w not in VACIAS}


def _clave_huella(titulo):
    """Huella estable de una noticia, para el histórico de usadas."""
    return hashlib.md5(" ".join(sorted(_palabras(titulo))[:8]).encode()).hexdigest()[:12]


def _misma_noticia(a, b):
    """Dos titulares son la misma noticia si comparten buena parte de sus palabras.

    El hash exacto no servía: cinco medios contaron la Ley Ángel con titulares
    distintos y el radar los tomaba como cinco noticias, así que las 2 piezas del
    día habrían sido la misma noticia dos veces.
    """
    pa, pb = _palabras(a), _palabras(b)
    if not pa or not pb:
        return False
    comunes = len(pa & pb)
    return comunes >= 3 and comunes / min(len(pa), len(pb)) >= 0.45


# ── Feeds DIRECTOS de los medios (probados el 12-sep-2026) ────────────────
# Google News sirve para descubrir, pero esconde el enlace real detrás de
# JavaScript y los buscadores bloquean las consultas automáticas. Sin la URL
# real no se puede leer el artículo, y sin el artículo la IA rellena con frases
# vacías. Estos feeds SÍ entregan la dirección verdadera.
FEEDS = [
    ("Infobae Colombia", "https://www.infobae.com/arc/outboundfeeds/rss/category/colombia/"),
    ("Semana",           "https://www.semana.com/arc/outboundfeeds/rss/category/nacion/"),
    ("El Colombiano",    "https://www.elcolombiano.com/rss/colombia.xml"),
    ("El Tiempo",        "https://www.eltiempo.com/rss/vida.xml"),
    ("El Tiempo",        "https://www.eltiempo.com/rss/colombia.xml"),
    ("El Tiempo",        "https://www.eltiempo.com/rss/justicia.xml"),
    ("Minambiente",      "https://www.minambiente.gov.co/rss/"),
]
TEMA = re.compile(r"perro|gato|mascota|felin|canin|cachorro|animal|veterinar|zoo|"
                  r"bienestar animal|maltrato animal", re.I)


def bajar_feeds(dias=7):
    """Lee los feeds propios de los medios: traen la URL real del artículo."""
    import requests
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124"
    corte = datetime.now(timezone.utc) - timedelta(days=dias)
    salida, vistos = [], set()
    for medio, url in FEEDS:
        try:
            r = s.get(url, timeout=25)
            items = ET.fromstring(r.content).findall(".//item")
        except Exception:
            continue
        for it in items:
            enlace = (it.findtext("link") or "").strip()
            titulo = (it.findtext("title") or "").strip()
            resumen = re.sub("<[^>]+>", " ", it.findtext("description") or "")[:500]
            if not enlace or enlace in vistos or not TEMA.search(titulo + " " + resumen):
                continue
            f = it.findtext("pubDate", "") or ""
            fecha = None
            for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S"):
                try:
                    fecha = datetime.strptime(f.strip()[:31 if "%z" in fmt else 25].strip(), fmt)
                    break
                except Exception:
                    continue
            if fecha is None:
                fecha = datetime.now(timezone.utc)
            if fecha.tzinfo is None:
                fecha = fecha.replace(tzinfo=timezone.utc)
            if fecha < corte:
                continue
            vistos.add(enlace)
            salida.append({"titulo": titulo, "medio": medio, "url": enlace,
                           "fecha": fecha, "resumen": re.sub(r"\s+", " ", resumen).strip()})
    return salida


def bajar(consulta, dias=7):
    url = GN.format(urllib.parse.quote(f"{consulta} when:{dias}d"))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        xml = urllib.request.urlopen(req, timeout=30).read()
    except Exception as e:
        print(f"  (falló «{consulta[:34]}»: {e})", file=sys.stderr)
        return []
    salida = []
    for it in ET.fromstring(xml).findall(".//item"):
        titulo = (it.findtext("title") or "").strip()
        medio = it.findtext("{http://news.google.com/}source") or (
            titulo.split(" - ")[-1] if " - " in titulo else "")
        try:
            fecha = datetime.strptime(it.findtext("pubDate", "")[:25].strip(),
                                      "%a, %d %b %Y %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            fecha = datetime.now(timezone.utc)
        salida.append({"titulo": titulo.split(" - ")[0].strip(), "medio": medio.strip(),
                       "url": (it.findtext("link") or "").strip(), "fecha": fecha,
                       "resumen": re.sub("<[^>]+>", " ", it.findtext("description") or "")[:400]})
    return salida


def puntuar(n):
    t = _norm(n["titulo"] + " " + n["resumen"])
    if re.search(VETO, t):
        return 0, ["vetado por ruido"]
    p, por_que = 0, []
    # fuente
    m = _norm(n["medio"])
    peso_fuente = next((v for k, v in FUENTES.items() if k in m or k in _norm(n["url"])), 0)
    if peso_fuente == 0:
        return 0, ["medio no reconocido"]
    p += peso_fuente; por_que.append(f"medio {n['medio'][:18]} (+{peso_fuente})")
    # frescura
    horas = (datetime.now(timezone.utc) - n["fecha"]).total_seconds() / 3600
    fresco = 20 if horas <= 24 else 14 if horas <= 72 else 8 if horas <= 168 else 3
    p += fresco; por_que.append(f"{horas:.0f} h (+{fresco})")
    # tema
    for rx, w in PESOS:
        if re.search(rx, t):
            p += w; por_que.append(f"tema (+{w})")
            break
    else:
        return 0, ["sin tema de interés"]
    # alcance
    if re.search(LOCAL_NUESTRO, t):
        p += 16; por_que.append("es de nuestra región (+16)")
    elif re.search(NACIONAL, t):
        p += 10; por_que.append("interés nacional (+10)")
    elif re.search(SOLO_BOGOTA, t):
        p -= 12; por_que.append("solo Bogotá (-12)")
    # que hable de perros o gatos
    if not re.search(r"perro|gato|mascota|animal|felin|canin|cachorro", t):
        return 0, ["no habla de perros ni gatos"]
    return p, por_que


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=7)
    ap.add_argument("--cuantas", type=int, default=2, help="piezas por día (Diego: 2)")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    crudas, vistas = [], set()
    for c in CONSULTAS:
        for n in bajar(c, a.dias):
            if n["url"] in vistas:
                continue
            vistas.add(n["url"]); crudas.append(n)
    # agrupar la misma noticia contada por varios medios: gana el titular de mejor puntaje
    utiles = []
    for n in crudas:
        n["puntaje"], n["por_que"] = puntuar(n)
        if n["puntaje"] > 0:
            utiles.append(n)
    utiles.sort(key=lambda x: -x["puntaje"])
    grupos = []
    for n in utiles:
        for g in grupos:
            if _misma_noticia(g["titulo"], n["titulo"]):
                g["repeticiones"] += 1
                g.setdefault("tambien_en", [])
                if n["medio"] and n["medio"] not in g["tambien_en"]:
                    g["tambien_en"].append(n["medio"])
                # Cada medio titula distinto y aporta datos que los otros no dan.
                # Google News no entrega el enlace real del artículo y los
                # buscadores bloquean las consultas automáticas, así que estas
                # variantes SON la materia prima de hechos para el guion.
                g.setdefault("variantes", [])
                if not any(v["titulo"] == n["titulo"] for v in g["variantes"]):
                    g["variantes"].append({"titulo": n["titulo"], "medio": n["medio"],
                                           "resumen": re.sub("<[^>]+>", " ", n["resumen"])[:260]})
                break
        else:
            n["repeticiones"] = 1; n["variantes"] = []; grupos.append(n)
    # que varios medios la cuenten es señal de que importa
    for n in grupos:
        if n["repeticiones"] > 1:
            extra = min(12, 4 * (n["repeticiones"] - 1))
            n["puntaje"] += extra
            n["por_que"].append(f"la cuentan {n['repeticiones']} medios (+{extra})")
    orden = sorted(grupos, key=lambda x: -x["puntaje"])

    # DIVERSIDAD: dos titulares pueden ser desarrollos del mismo hecho aunque estén
    # redactados muy distinto ("reglamentan la Ley Ángel" y "así es la nueva ruta
    # para denunciar"). Para las piezas del día se exige que no compartan más de
    # una palabra fuerte con algo ya elegido.
    elegidas, descartadas_por_parecido = [], []
    for n in orden:
        pn = _palabras(n["titulo"])
        if any(len(pn & _palabras(e["titulo"])) >= 2 for e in elegidas):
            descartadas_por_parecido.append(n); continue
        elegidas.append(n)
        if len(elegidas) >= a.cuantas:
            break

    print(f"{len(crudas)} titulares leídos · {len(orden)} noticias útiles tras filtrar\n")
    ids_elegidas = {id(x) for x in elegidas}
    for i, n in enumerate(orden[:12], 1):
        marca = "  << SE CONVIERTE EN VIDEO" if id(n) in ids_elegidas else (
            "  (parecida a una ya elegida)" if n in descartadas_por_parecido else "")
        print(f"{i:2d}. [{n['puntaje']:>3}] {n['titulo'][:76]}{marca}")
        print(f"     {n['medio'][:22]:24} {n['fecha'].astimezone(BOGOTA):%d-%b %H:%M}   {' · '.join(n['por_que'])}")
        if n.get("tambien_en"):
            print(f"     también en: {', '.join(n['tambien_en'][:5])}")
    if a.json:
        json.dump([{**n, "fecha": n["fecha"].isoformat()} for n in elegidas],
                  open(a.json, "w"), ensure_ascii=False, indent=1)
        print(f"\nlas {a.cuantas} elegidas -> {a.json}")


if __name__ == "__main__":
    main()
