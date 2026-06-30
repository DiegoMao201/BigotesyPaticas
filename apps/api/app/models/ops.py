"""Modelos cross-cutting (`ops`): legacy_id_map, audit_log."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common import Base, TimestampMixin, UUIDPKMixin


class LegacyIdMap(UUIDPKMixin, TimestampMixin, Base):
    """Tabla puente entre IDs nuevos (UUID en PG) e IDs antiguos (Sheets)."""

    __tablename__ = "legacy_id_map"
    __table_args__ = (
        UniqueConstraint("entity", "legacy_id", name="uq_legacy_id_map_entity_legacy_id"),
        {"schema": "ops"},
    )

    entity: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    legacy_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    new_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class AuditLog(UUIDPKMixin, Base):
    """Audit log inmutable. Append-only."""

    __tablename__ = "audit_log"
    __table_args__ = ({"schema": "ops"},)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    actor: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
