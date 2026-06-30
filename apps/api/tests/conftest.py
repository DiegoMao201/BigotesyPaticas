# Tests del backend FastAPI
import os

os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:devpass@localhost:5432/bp_test"
)
os.environ.setdefault(
    "DATABASE_URL_SYNC", "postgresql+psycopg://postgres:devpass@localhost:5432/bp_test"
)
os.environ.setdefault("JWT_SECRET", "test-secret-very-long-not-default-xyz")
