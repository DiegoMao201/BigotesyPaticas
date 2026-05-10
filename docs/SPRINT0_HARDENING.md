# Sprint 0 — Hardening Streamlit

> Estado: ENTREGADO 2026-05-10. Todo opt-in: la app Streamlit actual NO ha sido modificada.

## Qué entregamos

### 1. Paquete compartido `bp_common/` (nuevo)
Funciones críticas reescritas como librería **bit-exact** respecto a las copias originales:
- [bp_common/currency.py](../bp_common/currency.py) — `clean_currency`, `money_int/float`, `format_cop`.
- [bp_common/ids.py](../bp_common/ids.py) — `normalizar_id_producto`, `limpiar_tel`.
- [bp_common/pricing.py](../bp_common/pricing.py) — `precio_con_margen` (P = C / (1 - m)).
- [bp_common/payments.py](../bp_common/payments.py) — `normalizar_estado_pago`.
- [bp_common/tz.py](../bp_common/tz.py) — `TZ_CO`, `now_co`, `get_bogota_timezone`.
- [bp_common/sheets_sanitize.py](../bp_common/sheets_sanitize.py) — `sanitizar_para_sheet`.
- [bp_common/flags.py](../bp_common/flags.py) — feature flags por env + override runtime.
- [bp_common/audit.py](../bp_common/audit.py) — escribe a tab `Audit_Log` del spreadsheet (no bloqueante).
- [bp_common/version_info.py](../bp_common/version_info.py) — versión + git SHA + env, badge para sidebar.
- [bp_common/logging_setup.py](../bp_common/logging_setup.py) — logging JSON estructurado.

### 2. Tests golden ([tests/](../tests/))
- `tests/golden/test_currency_golden.py` — 25+ casos.
- `tests/golden/test_ids_golden.py`.
- `tests/golden/test_pricing_golden.py`.
- `tests/golden/test_payments_golden.py`.
- `tests/unit/test_flags_version_logging.py`.
- `tests/unit/test_sheets_sanitize.py`.

Ejecutar: `pytest -q` → debe estar verde antes de cualquier refactor.

### 3. Calidad / DX
- [pyproject.toml](../pyproject.toml) — ruff (lint+format), pytest, coverage, mypy.
  - Streamlit legacy (`BigotesyPaticas.py`, `pages/*`) está EXENTO del linter para no introducir cambios destructivos. Se irá habilitando módulo por módulo.
- [requirements.txt](../requirements.txt) — versiones **pineadas** (eliminado `twilio` no usado).
- [requirements-dev.txt](../requirements-dev.txt) — pytest, ruff, mypy, pre-commit, pyarrow, boto3.
- [.pre-commit-config.yaml](../.pre-commit-config.yaml) — trailing-whitespace, ruff, gitleaks, detect-private-key.
- [.gitleaks.toml](../.gitleaks.toml) — reglas custom (Google SA private key, OpenRouter, DO Spaces, Gmail App Passwords).

### 4. CI/CD
- [.github/workflows/ci.yml](../.github/workflows/ci.yml) — lint + tests py3.11/3.12 + secrets scan.

### 5. Backups automáticos
- [scripts/backup_sheets.py](../scripts/backup_sheets.py) — exporta todas las tabs a CSV + Parquet con manifest JSON.
- Para programar diario en Coolify (cron job o servicio scheduled):
  ```bash
  python scripts/backup_sheets.py --out backups/$(date +%Y-%m-%d)
  ```
- Recomendado: subir a Spaces/MinIO con `aws s3 sync backups/ s3://bucket/sheets-backups/` o equivalente.

## Cómo activar todo localmente

```bash
# 1. Instalar deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# 2. Pre-commit
pre-commit install

# 3. Tests
pytest -q

# 4. Backup manual
python scripts/backup_sheets.py
```

## Lo que SÍ se modificó del repo

- `requirements.txt`: pineado, sin `twilio`.
- `project-secrets/.env.production.example`: limpiado tras incidente del 2026-05-10 (ver `INCIDENT_2026-05-10_secrets_in_example.md`).

## Lo que NO se modificó

- `BigotesyPaticas.py` ✅ intacto.
- `pages/*.py` ✅ intactos.
- `factura.html` ✅ intacto.
- Configuración de Streamlit Cloud ✅ intacta.

## Próximos pasos (siguen en autonomía)

1. **Fase 1 — Fundación infraestructura**: docker-compose, Postgres, Redis, MinIO, esqueletos `apps/api` y `apps/admin`.
2. **Fase 2 — Database foundation**: schemas Alembic, ETL Sheets→PG.
3. Adopción gradual de `bp_common/*` en Streamlit cuando sea seguro (módulo por módulo, con tests golden corriendo).
