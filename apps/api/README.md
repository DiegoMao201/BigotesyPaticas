# Bigotes y Paticas API

FastAPI backend enterprise. Postgres + SQLAlchemy 2 + Alembic + Pydantic v2 + JWT (RBAC).

## Endpoints clave

- `GET /health` — liveness probe.
- `GET /version` — versión + git SHA.
- `POST /v1/auth/login` — login email/password → JWT.
- `GET /v1/auth/me` — info del usuario autenticado.
- `GET /v1/products` — catálogo paginado, filtros, búsqueda.
- `POST /v1/products` — crear producto (admin).
- `GET /v1/inventory/stock/{sku}` — stock actual.
- `POST /v1/sales/orders` — crear orden (atómico, descuenta stock).
- `GET /v1/sales/orders/{id}` — detalle de orden.

Docs interactivas: `http://localhost:8000/docs` (dev).

## Desarrollo

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env  # ajusta DATABASE_URL si es necesario

# Migraciones
alembic upgrade head

# Servidor
uvicorn app.main:app --reload --port 8000
```

## Estructura

```
app/
  main.py              FastAPI app + middleware + routers
  config.py            Settings (pydantic-settings)
  db.py                SQLAlchemy engine + session
  deps.py              Dependencias (current_user, db)
  security.py          JWT + password hashing
  middleware.py        Request ID, logging, error handler
  api/
    v1/
      auth.py          Login, me
      products.py      Catálogo
      inventory.py     Stock
      sales.py         Órdenes
      health.py        Health/version
  models/              SQLAlchemy ORM (un módulo por context)
    auth.py
    catalog.py
    inventory.py
    sales.py
    common.py          Base, mixins (TimestampMixin, SoftDeleteMixin)
  schemas/             Pydantic v2 (request/response)
  services/            Lógica de negocio (transactional)
  repositories/        Acceso a datos
alembic/               Migraciones
tests/                 Pytest
```

## Migraciones

```bash
alembic revision --autogenerate -m "add table xyz"
alembic upgrade head
alembic downgrade -1
```

## Tests

```bash
pytest -q
```
