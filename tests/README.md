# Tests

Esta carpeta contiene la suite de tests automatizados.

## Estructura

- `golden/` — Tests **bit-exact** que comparan funciones nuevas en `bp_common/` contra el comportamiento original de `BigotesyPaticas.py` y `pages/*.py`. Cualquier diff ROMPE la build.
- `unit/` — Tests unitarios puros sobre `bp_common/`.
- `integration/` — (futuro) tests contra Sheets/PG con fixtures.

## Ejecutar

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Política

- Los **golden tests** definen el contrato. Si necesitas cambiar el comportamiento
  de `clean_currency`, `normalizar_id_producto`, `precio_con_margen` o
  `_normalizar_estado_pago`, actualiza primero el golden, justifica el cambio en
  un PR y obtén aprobación de negocio.
- Cobertura objetivo en `bp_common/`: ≥ 90%.
