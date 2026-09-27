"""Pasada automática de la bandeja de facturas (cada 5 min, desde start.sh).

Lee el correo de Bigotes (solo lectura) y deja en purchasing.inbox_invoices las
facturas DIAN nuevas de los últimos 3 días. Si falta el acceso al correo, no hace
nada y no rompe el ciclo de las demás tareas. El log lleva solo ids, NIT y estado:
nunca contenido de correos.
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, "/app")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


async def main() -> None:
    if not os.environ.get("GMAIL_BP_REFRESH_TOKEN"):
        return
    from app.db import AsyncSessionLocal
    from app.services.facturas_correo import sincronizar
    async with AsyncSessionLocal() as db:
        r = await sincronizar(db, dias=3)
    if r.get("nuevos"):
        logging.getLogger("facturas_correo").info("pasada: %s", r)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:   # un fallo del correo no debe tumbar el ciclo
        logging.getLogger("facturas_correo").error("fallo: %s", type(e).__name__)
