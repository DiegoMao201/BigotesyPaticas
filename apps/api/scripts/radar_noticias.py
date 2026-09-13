#!/usr/bin/env python3
"""Radar de noticias en el servidor. Corre 4 veces al día (6, 11, 16 y 21 Bogotá).

Solo DETECTA y guarda: no escribe guiones ni arma videos. El video se arma en el
Mac de Diego, porque este contenedor tiene 2 vCPU y atiende tienda, portal y admin;
un render aquí los pondría lentos.

Lo llama el mismo bucle de 5 minutos de start.sh; el propio script decide si le
toca correr, mirando la última corrida en content.engine_config.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psycopg
import _leer_articulo as LA
import _radar_core as R

BOGOTA = timezone(timedelta(hours=-5))
HORAS = (6, 11, 16, 21)
CLAVE = "radar_noticias_ultima"
MIN_CUERPO = 1800


def toca_ahora(cur) -> bool:
    if "--forzar" in sys.argv:
        return True
    ahora = datetime.now(BOGOTA)
    if ahora.hour not in HORAS:
        return False
    cur.execute("SELECT value FROM content.engine_config WHERE key = %s", (CLAVE,))
    fila = cur.fetchone()
    if fila and fila[0]:
        try:
            ultima = datetime.fromisoformat(fila[0])
            if (ahora - ultima).total_seconds() < 3000:      # ya corrió esta hora
                return False
        except ValueError:
            pass
    return True


def marcar(cur):
    cur.execute("""
        INSERT INTO content.engine_config (key, value) VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    """, (CLAVE, datetime.now(BOGOTA).isoformat()))


def main():
    dsn = os.environ.get("DATABASE_URL", "").replace("+psycopg", "").replace("+asyncpg", "")
    with psycopg.connect(dsn) as con:
        cur = con.cursor()
        if not toca_ahora(cur):
            # Deja constancia de que SÍ se ejecutó aunque no le tocara. Sin esto el
            # log queda en cero bytes y no hay forma de distinguir "corrió y pasó
            # de largo" de "nunca arrancó", que es exactamente la duda que hubo
            # el 12-sep cuando el radar llevaba días sin estar enchufado.
            print(f"{datetime.now(BOGOTA):%Y-%m-%d %H:%M}  sin turno (corre a las {', '.join(map(str, HORAS))})", flush=True)
            return
        marcar(cur); con.commit()
        sesion = LA._sesion()
        nuevas = leidas = 0
        for n in R.bajar_feeds(7):
            huella = R._clave_huella(n["titulo"])
            cur.execute("SELECT 1 FROM content.noticias_radar WHERE huella = %s", (huella,))
            if cur.fetchone():
                continue
            puntaje, por_que = R.puntuar(n)
            estado, motivo, cuerpo = "descartada", "; ".join(por_que), ""
            if puntaje >= 30:
                cuerpo = LA.leer(n["url"], sesion)
                leidas += 1
                if len(cuerpo) >= MIN_CUERPO:
                    estado, motivo = "lista", None
                else:
                    motivo = f"artículo de solo {len(cuerpo)} caracteres"
            cur.execute("""
                INSERT INTO content.noticias_radar
                  (huella, titulo, medio, url, fecha_noticia, puntaje, cuerpo_chars, estado, motivo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (huella) DO NOTHING
            """, (huella, n["titulo"][:400], n["medio"][:80], n["url"], n["fecha"],
                  puntaje, len(cuerpo), estado, (motivo or "")[:400] or None))
            nuevas += 1
        con.commit()
        cur.execute("SELECT count(*) FROM content.noticias_radar WHERE estado = 'lista'")
        print(f"{datetime.now(BOGOTA):%Y-%m-%d %H:%M} radar: {nuevas} nuevas, "
              f"{leidas} artículos leídos, {cur.fetchone()[0]} listas para armar")


if __name__ == "__main__":
    main()
