"""Reconocer un código de barras de producto (GTIN/EAN) por su dígito de control."""

from __future__ import annotations

import re


def es_gtin_unidad(code: str) -> bool:
    """True si `code` es un EAN-8, UPC-A (12) o EAN-13 válido de venta al público.

    Se excluye el GTIN-14: es el código de la CAJA (Quantum factura la arena
    AuraPro "X 4UND" con 17709197349342) y la pistola en la tienda lee la bolsa.
    Se excluyen también los EAN-13 que empiezan por 2: son de circulación interna
    (balanzas, códigos propios de cada almacén), no identifican el producto.
    """
    if not re.fullmatch(r"\d{8}|\d{12,13}", code or ""):
        return False
    if len(code) == 13 and code[0] == "2":
        return False
    digitos = [int(c) for c in code]
    cuerpo = digitos[:-1][::-1]
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(cuerpo))
    return (10 - total % 10) % 10 == digitos[-1]
