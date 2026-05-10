# scripts/

Utilities operacionales del proyecto. **No corren en producción**, son herramientas locales/CI.

## media/
- `optimize_images.py` — convierte originales a WebP + variantes responsive (thumb/card/main/zoom)
- `upload_to_spaces.py` — sube `local-assets/optimized/` a DO Spaces (idempotente vía MD5 ETag)
- `validate_naming.py` — verifica que los archivos cumplen `docs/IMAGE_NAMING_GUIDE.md`

Pipeline típico:
```bash
# 1. Drop fotos en local-assets/originals/<sku-slug>/
# 2. Optimizar → genera variantes WebP en local-assets/optimized/
python scripts/media/optimize_images.py --src local-assets/originals --dst local-assets/optimized
# 3. Validar naming
python scripts/media/validate_naming.py local-assets/optimized
# 4. Subir
set -a && source project-secrets/.env.production && set +a
python scripts/media/upload_to_spaces.py --src local-assets/optimized --dry-run
python scripts/media/upload_to_spaces.py --src local-assets/optimized
```

## etl/
- `sheets_to_pg.py` — migración de Google Sheets a PostgreSQL.

```bash
set -a && source project-secrets/.env.production && set +a
python scripts/etl/sheets_to_pg.py --list-tabs
python scripts/etl/sheets_to_pg.py --tab products --dry-run
python scripts/etl/sheets_to_pg.py --all
```

Salida: `etl_logs/etl-<ts>.json` con conteos y filas rechazadas.

Variables de entorno requeridas:
- `GOOGLE_SHEETS_CREDENTIALS_JSON` — path a service account JSON
- `GOOGLE_SHEET_ID` — ID del sheet de origen
- `DATABASE_URL_SYNC` — Postgres del API
