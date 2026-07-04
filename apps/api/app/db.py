"""SQLAlchemy 2 — async engine + sessionmaker + Base declarativa."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any, ClassVar

from sqlalchemy import MetaData, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# Convención de nombres para constraints — esencial para Alembic
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: ClassVar[dict[Any, Any]] = {}


engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,        # detecta conexiones muertas antes de usarlas
    pool_recycle=1800,         # recicla conexiones cada 30 min para evitar stale sockets
    pool_timeout=30,           # espera máx 30 s para obtener una conexión del pool
    echo=False,
)


@event.listens_for(engine.sync_engine, "connect")
def _on_connect(dbapi_connection: Any, connection_record: Any) -> None:
    """Registra codecs JSON/JSONB para asyncpg 0.28+ que no los registra automáticamente."""
    raw = dbapi_connection.driver_connection
    raw.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog", format="text")
    raw.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog", format="text")


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia FastAPI: cede una sesión y maneja commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
