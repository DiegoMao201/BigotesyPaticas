"""Pone `attributes.peso_kg` a todos los productos publicados (16-oct-2026).

Diego: *"el peso: los concentrados sí lo traen en su descripción, pero el resto
pueden ser miligramos, gramos o incluso nada como los accesorios o algunos snacks;
ármalos tú consultando los productos"*.

La transportadora cobra por kilos y por volumen; sin peso no hay cotización
honesta. Este script decide el peso de CADA producto con dos fuentes, en orden:

1. **El nombre**, cuando trae la cantidad ("15k", "3,5 Lb (1,59 Kg)", "5,5 Oz",
   "4x14g"). Es lo que dice el empaque. Para medicamentos, un "10-20 Kg" es el
   peso del perro y se ignora.
2. **Una regla por tipo de producto** para lo que no lo trae: un collar, una pala,
   un hueso, una caja de tabletas. Son pesos de referencia del artículo tal como
   se vende (con su empaque), redondeados hacia arriba para no cotizar de menos.

Uso (desde apps/api):
    python scripts/pesos_productos.py productos.txt > pesos.csv
    python scripts/pesos_productos.py productos.txt --sql > pesos.sql

`productos.txt` sale de psql con separador `@@@` (el tabulador se pierde por ssh):
    select p.id, p.sku, p.name, coalesce(c.name,''), coalesce(pc.name,''),
           coalesce(b.name,''), p.price, p.attributes::text
    from catalog.products p left join catalog.categories c on c.id=p.category_id
    left join catalog.categories pc on pc.id=c.parent_id
    left join catalog.brands b on b.id=p.brand_id
    where p.deleted_at is null and p.is_published

El SQL que produce es idempotente: solo escribe `peso_kg` y `peso_fuente` dentro
del JSONB, sin tocar lo demás. Un peso puesto a mano por el admin (fuente
'manual') no se pisa.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import envia

#: (patrón en el nombre, kilos). Se evalúan en orden; gana el primero que cuadre.
#: Los pesos incluyen el empaque del artículo tal como se despacha.
REGLAS: list[tuple[str, float]] = [
    # Accesorios
    (r"morral|transportador|guacal|cápsula|capsula", 1.4),
    (r"comedero.*(ceramica|cerámica)", 0.9),
    (r"comedero.*silicona", 0.6),
    (r"comedero|bebedero|dispensador de agua", 0.4),
    (r"correa retr", 0.35),
    (r"correa|arnes|arnés|pechera", 0.25),
    (r"isabelino|isabilino", 0.15),
    (r"collar", 0.12),
    (r"placa", 0.05),
    (r"cuchara", 0.05),
    (r"\bcama\b|colch[oó]n", 1.2),
    # Higiene y cuidado
    (r"pala .*metal|pala herragro|recogedera", 0.5),
    (r"pala", 0.3),
    (r"pañitos.*100", 0.55),
    (r"pañitos.*80", 0.45),
    (r"pañitos.*50", 0.3),
    (r"pañitos.*10 ", 0.08),
    (r"pañitos|toallitas", 0.3),
    (r"pañal", 0.06),
    (r"dispensador de bolsas", 0.06),
    (r"peinera|cepillo|peine", 0.12),
    (r"crema dental", 0.15),
    (r"arena", 4.5),
    # Juguetes
    (r"llanta", 0.5),
    (r"astronauta|dispensador de comida", 0.3),
    (r"juguete|erizo|nudo|mordedor|pelota", 0.2),
    # Medicamentos y suplementos (caja o frasco)
    (r"nuggets|masticables|comp\b|tab\b|tabs\b|tableta|blister|cja|caps", 0.1),
    (r"omega|jarabe|gotas|suspension|suspensión|fco", 0.2),
    # Snacks sin peso en el nombre
    (r"calambombo", 0.6),
    (r"mini femur|hueso mini", 0.12),
    (r"femur", 0.3),
    (r"hueso", 0.12),
    (r"lata", 0.17),
    (r"galleta|croquis", 0.15),
    (r"churu|cremoso|duo cup|minican|mousse|patee|paté", 0.1),
    (r"palitos|lonchas|patatas", 0.08),
    # Alimento seco sin cantidad: es un sobre o una muestra
    (r"instinctive|pouch|sobre", 0.09),
]

DEFECTO_POR_CATEGORIA = {
    "ACCESORIOS": 0.3,
    "HIGIENE Y CUIDADO": 0.3,
    "JUGUETES": 0.2,
    "MEDICAMENTOS": 0.1,
    "SNACKS": 0.12,
    "ALIMENTO SECO": 1.0,
    "ALIMENTO MEDICADO": 1.0,
    "ALIMENTO NATURAL": 0.5,
}


def _del_nombre(nombre: str, categoria: str) -> float | None:
    """Peso según el nombre, o None si no trae cantidad utilizable."""
    texto = nombre or ""
    rango_animal = bool(envia._RANGO_ANIMAL.search(texto))
    cands: list[float] = []
    for cant, val, u in envia._MULTI.findall(texto):
        cands.append(int(cant) * envia._a_kg(float(val.replace(",", ".")), u))
    for val, u in envia._UNIDAD.findall(texto):
        es_kilo = u.lower() in ("kg", "k", "kl", "kilo", "kilos")
        # En medicamentos los kilos del nombre son casi siempre del animal
        # ("Bravecto 10-20 Kg", "Nexgard 25-50 Kg"): no cuentan nunca.
        if es_kilo and (rango_animal or categoria == "MEDICAMENTOS"):
            continue
        cands.append(envia._a_kg(float(val.replace(",", ".")), u))
    cands = [c for c in cands if 0 < c <= 60]
    if not cands:
        return None
    kg = max(cands)
    # Un líquido o una pasta pesa un poco más que su volumen por el frasco; una
    # tableta de "200mg" no pesa 0,2 g sino su caja. Se corrige con un mínimo.
    if categoria == "MEDICAMENTOS":
        kg = max(kg * 1.2, 0.08)
    elif categoria in ("HIGIENE Y CUIDADO", "SNACKS") and kg < 2:
        kg = max(kg * 1.1, 0.05)
    return round(kg, 3)


def decidir(nombre: str, categoria: str) -> tuple[float, str]:
    kg = _del_nombre(nombre, categoria)
    if kg is not None:
        return kg, "nombre"
    n = nombre.lower()
    for patron, peso in REGLAS:
        if re.search(patron, n):
            return peso, "regla"
    return DEFECTO_POR_CATEGORIA.get(categoria, 0.5), "categoria"


def main() -> None:
    ruta = sys.argv[1]
    sql = "--sql" in sys.argv
    with open(ruta, encoding="utf-8") as f:
        filas = [linea.rstrip("\n").split("@@@") for linea in f if "@@@" in linea]
    out = csv.writer(sys.stdout)
    if not sql:
        out.writerow(["id", "sku", "categoria", "nombre", "precio", "peso_kg", "fuente"])
    for pid, sku, nombre, cat, _padre, _marca, precio, attrs in filas:
        try:
            actuales = json.loads(attrs or "{}") or {}
        except ValueError:
            actuales = {}
        kg, fuente = decidir(nombre, cat)
        if actuales.get("peso_fuente") == "manual" and actuales.get("peso_kg"):
            kg, fuente = float(actuales["peso_kg"]), "manual"
        if sql:
            if fuente == "manual":
                continue
            print(
                f"UPDATE catalog.products SET attributes = coalesce(attributes,'{{}}'::jsonb) || "
                f"'{{\"peso_kg\": {kg}, \"peso_fuente\": \"{fuente}\"}}'::jsonb WHERE id = '{pid}';"
            )
        else:
            out.writerow([pid, sku, cat, nombre, precio, kg, fuente])


if __name__ == "__main__":
    main()
