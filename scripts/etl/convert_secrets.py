#!/usr/bin/env python3
"""
Convierte las credenciales de Google Service Account desde formato TOML
(como las guarda Streamlit Cloud) a JSON listo para gspread.

USO:
  1. Ve a Streamlit Cloud → tu app → Settings → Secrets
  2. Copia el bloque [google_service_account] INCLUYENDO el header
  3. Pega en un archivo: project-secrets/streamlit-secrets.toml
  4. Ejecuta:
       python3 scripts/etl/convert_secrets.py
  5. Resultado: project-secrets/google-service-account.json
  6. Luego ejecuta el ETL:
       GOOGLE_SHEETS_CREDENTIALS_JSON=project-secrets/google-service-account.json \
       GOOGLE_SHEET_ID=12ay8_vug1yYXoGhHCIjKy1_NL5oqz6QBQ537283iGEo \
       DATABASE_URL_SYNC="postgresql+psycopg://..." \
       python3 scripts/etl/sheets_to_pg.py --all

ALTERNATIVA rápida: si ya tienes el JSON de service account descargado de
Google Cloud Console, simplemente cópialo a project-secrets/google-service-account.json
y pasa al paso 6 directamente.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # pip install tomli
    except ImportError:
        print("ERROR: Necesitas Python 3.11+ o: pip install tomli", file=sys.stderr)
        sys.exit(1)

ROOT = Path(__file__).parent.parent.parent
SECRETS_TOML = ROOT / "project-secrets" / "streamlit-secrets.toml"
OUTPUT_JSON = ROOT / "project-secrets" / "google-service-account.json"

if not SECRETS_TOML.exists():
    print(f"ERROR: No se encontró {SECRETS_TOML}")
    print("\nPasos:")
    print("  1. Ve a Streamlit Cloud → Settings → Secrets")
    print("  2. Copia TODO el contenido")
    print(f"  3. Guárdalo en: {SECRETS_TOML}")
    print("  4. Vuelve a ejecutar este script")
    sys.exit(1)

data = tomllib.loads(SECRETS_TOML.read_text())

if "google_service_account" not in data:
    print("ERROR: No se encontró la sección [google_service_account] en el TOML")
    sys.exit(1)

sa = dict(data["google_service_account"])
# Normalizar private_key: los \n literales del TOML deben ser saltos de línea reales
if "private_key" in sa:
    sa["private_key"] = sa["private_key"].replace("\\n", "\n")

OUTPUT_JSON.write_text(json.dumps(sa, indent=2, ensure_ascii=False))
print(f"✅ Service account guardada en: {OUTPUT_JSON}")
print(f"   client_email: {sa.get('client_email', 'N/A')}")
print(f"   project_id:   {sa.get('project_id', 'N/A')}")
print()
print("Siguiente paso — ejecutar el ETL:")
print(f"""
  export GOOGLE_SHEETS_CREDENTIALS_JSON="{OUTPUT_JSON}"
  export GOOGLE_SHEET_ID="12ay8_vug1yYXoGhHCIjKy1_NL5oqz6QBQ537283iGEo"
  export DATABASE_URL_SYNC="postgresql+psycopg2://USER:PASS@HOST:5432/DB"
  python3 scripts/etl/sheets_to_pg.py --list-tabs
  python3 scripts/etl/sheets_to_pg.py --all --dry-run
  python3 scripts/etl/sheets_to_pg.py --all
""")
