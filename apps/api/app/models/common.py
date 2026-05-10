"""Modelos base y mixins compartidos."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.db import Base


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, index=True
    )


class AuditMixin:
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)


__all__ = ["Base", "UUIDPKMixin", "TimestampMixin", "SoftDeleteMixin", "AuditMixin"]


def model_to_dict(obj: Any) -> dict[str, Any]:
    """Serializa un modelo SQLAlchemy a dict (útil en tests/debug)."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}  # type: ignore[union-attr]


# Pequeño helper para que los modelos hereden tablename automático
class TablenameMixin:
    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore[override]
        # CamelCase → snake_case
        import re
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        return name
