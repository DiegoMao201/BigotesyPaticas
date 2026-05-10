# BigotesyPaticas

Plataforma operativa de un pet shop (POS, CRM, inventario, compras, finanzas, loyalty) construida sobre Streamlit + Google Sheets.

> ⚙️ **Estado actual:** producción operativa sobre Streamlit. La aplicación NO se apaga ni se modifica destructivamente.
> 🚀 **Plan:** evolución progresiva (strangler fig) hacia una arquitectura moderna (FastAPI + PostgreSQL + Next.js) sin downtime, documentada en [docs/](docs/).

---

## Estructura del repositorio

| Carpeta / archivo | Propósito |
|-------------------|-----------|
| [BigotesyPaticas.py](BigotesyPaticas.py) | Entry point Streamlit (POS, sync) |
| [pages/](pages/) | Módulos de negocio (5 páginas) |
| [factura.html](factura.html) | Template Jinja2 para PDF de factura |
| [requirements.txt](requirements.txt) · [packages.txt](packages.txt) | Dependencias Python y de sistema |
| [docs/](docs/) | **Documentación arquitectónica y plan de migración** |
| [project-secrets/](project-secrets/) | Plantillas de secretos (sólo `.example`, nunca valores reales) |

---

## Documentación clave

Antes de proponer cualquier cambio arquitectónico, leer en este orden:

1. [docs/project-continuity.md](docs/project-continuity.md) — decisiones vigentes y bitácora.
2. [docs/SYSTEM_AUDIT.md](docs/SYSTEM_AUDIT.md) — estado real del sistema.
3. [docs/ARCHITECTURE_ANALYSIS.md](docs/ARCHITECTURE_ANALYSIS.md) — AS-IS y TO-BE.
4. [docs/MIGRATION_MASTER_PLAN.md](docs/MIGRATION_MASTER_PLAN.md) — fases F0→F6.
5. [docs/DATABASE_STRATEGY.md](docs/DATABASE_STRATEGY.md) · [docs/API_STRATEGY.md](docs/API_STRATEGY.md) · [docs/FRONTEND_STRATEGY.md](docs/FRONTEND_STRATEGY.md) · [docs/DEVOPS_STRATEGY.md](docs/DEVOPS_STRATEGY.md)
6. [docs/TECH_DEBT_REPORT.md](docs/TECH_DEBT_REPORT.md) — backlog priorizado.

---

## Setup local de la app actual (Streamlit)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Configurar .streamlit/secrets.toml con SHEET_URL y google_service_account
streamlit run BigotesyPaticas.py
```

Ver [project-secrets/SECRETS_SETUP.md](project-secrets/SECRETS_SETUP.md) para los secretos requeridos.

---

## Reglas de oro para colaboradores (humanos o IA)

1. **No apagar Streamlit.** No introducir cambios destructivos en producción.
2. **Toda decisión arquitectónica nueva** se registra en [docs/project-continuity.md](docs/project-continuity.md).
3. **Secretos jamás en el repo.** Sólo plantillas `*.example` en [project-secrets/](project-secrets/).
4. **Lógica de negocio crítica** (`registrar_venta`, `precio_con_margen`, `_normalizar_estado_pago`, `clean_currency`) se preserva 1:1 hasta tener tests golden.
5. Cualquier flip de módulo en la migración debe ser **reversible en <5 min** vía feature flag.
