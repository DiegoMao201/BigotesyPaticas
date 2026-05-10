# =============================================================================
# Bigotes y Paticas — Orquestación de desarrollo local
# =============================================================================
SHELL := /bin/bash
.DEFAULT_GOAL := help

# ---- Infraestructura ---------------------------------------------------------
.PHONY: infra-up infra-down infra-logs infra-ps infra-reset
infra-up: ## Levanta Postgres + Redis + MinIO + Mailhog
	docker compose -f infrastructure/docker/docker-compose.yml up -d
	@echo "✓ Infra arriba."

infra-down: ## Para la infra (preserva volúmenes)
	docker compose -f infrastructure/docker/docker-compose.yml down

infra-logs: ## Logs de la infra
	docker compose -f infrastructure/docker/docker-compose.yml logs -f --tail=100

infra-ps: ## Estado de contenedores
	docker compose -f infrastructure/docker/docker-compose.yml ps

infra-reset: ## ⚠️ BORRA volúmenes locales (Postgres, MinIO, etc.)
	docker compose -f infrastructure/docker/docker-compose.yml down -v

# ---- Backend (FastAPI) -------------------------------------------------------
.PHONY: api-install api-dev api-migrate api-revision api-test
api-install: ## Instala dependencias del backend
	cd apps/api && python -m pip install -r requirements.txt -r requirements-dev.txt

api-dev: ## Corre la API en modo dev con autoreload
	cd apps/api && uvicorn app.main:app --reload --port 8000

api-migrate: ## Aplica migraciones Alembic
	cd apps/api && alembic upgrade head

api-revision: ## Crea revisión Alembic. Uso: make api-revision m="add table X"
	cd apps/api && alembic revision --autogenerate -m "$(m)"

api-test: ## Tests del backend
	cd apps/api && pytest -q

# ---- Admin panel (Next.js) ---------------------------------------------------
.PHONY: admin-install admin-dev admin-build
admin-install:
	cd apps/admin && pnpm install

admin-dev:
	cd apps/admin && pnpm dev

admin-build:
	cd apps/admin && pnpm build

# ---- Storefront (Next.js) ----------------------------------------------------
.PHONY: store-install store-dev store-build
store-install:
	cd apps/store && pnpm install

store-dev:
	cd apps/store && pnpm dev

store-build:
	cd apps/store && pnpm build

# ---- Monorepo TS -------------------------------------------------------------
.PHONY: install dev build lint
install: ## Instala todo el monorepo Node (pnpm)
	pnpm install

dev: ## Corre admin + store en paralelo (turbo)
	pnpm dev

build: ## Build del monorepo
	pnpm build

lint: ## Lint del monorepo TS + Python
	pnpm lint && ruff check .

# ---- Streamlit legacy --------------------------------------------------------
.PHONY: streamlit-dev
streamlit-dev: ## Corre la app Streamlit legacy
	streamlit run BigotesyPaticas.py

# ---- Tests Python ------------------------------------------------------------
.PHONY: test test-cov
test:
	pytest -q

test-cov:
	pytest --cov=bp_common --cov-report=term-missing -q

# ---- Backups -----------------------------------------------------------------
.PHONY: backup-sheets
backup-sheets: ## Exporta todas las tabs del sheet a CSV+Parquet
	python scripts/backup_sheets.py

# ---- Help --------------------------------------------------------------------
.PHONY: help
help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
