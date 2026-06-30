"""Modelos del bounded context `auth`."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import (
    AuditMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPKMixin,
)

# Tabla de unión users <-> roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("auth.roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    schema="auth",
)


class User(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"), {"schema": "auth"})

    email: Mapped[str] = mapped_column(CITEXT, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list[Role]] = relationship(
        "Role", secondary=user_roles, back_populates="users", lazy="selectin"
    )

    def has_permission(self, perm: str) -> bool:
        if self.is_superadmin:
            return True
        return any(perm in r.permissions for r in self.roles)


class Role(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("name", name="uq_roles_name"), {"schema": "auth"})

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    permissions: Mapped[list[str]] = mapped_column(
        # JSONB array of permission strings: ["catalog:read", "sales:write", ...]
        # SQLAlchemy will use ARRAY(TEXT) en Postgres.
        # Importamos aquí para evitar ciclos.
        __import__("sqlalchemy.dialects.postgresql", fromlist=["ARRAY"]).ARRAY(String),
        default=list,
        nullable=False,
    )

    users: Mapped[list[User]] = relationship(User, secondary=user_roles, back_populates="roles")


# Permisos canónicos (verdad única). Usar en seeds y RBAC.
PERMISSIONS = {
    # catalog
    "catalog:read",
    "catalog:write",
    # inventory
    "inventory:read",
    "inventory:write",
    "inventory:adjust",
    # sales
    "sales:read",
    "sales:write",
    "sales:refund",
    # purchasing
    "purchasing:read",
    "purchasing:write",
    # crm
    "crm:read",
    "crm:write",
    # finance
    "finance:read",
    "finance:write",
    # admin
    "users:read",
    "users:write",
    "settings:write",
}

ROLE_DEFAULTS = {
    "superadmin": list(PERMISSIONS),
    "admin": [
        "catalog:read",
        "catalog:write",
        "inventory:read",
        "inventory:write",
        "inventory:adjust",
        "sales:read",
        "sales:write",
        "sales:refund",
        "purchasing:read",
        "purchasing:write",
        "crm:read",
        "crm:write",
        "finance:read",
        "finance:write",
        "users:read",
    ],
    "manager": [
        "catalog:read",
        "catalog:write",
        "inventory:read",
        "inventory:write",
        "inventory:adjust",
        "sales:read",
        "sales:write",
        "purchasing:read",
        "purchasing:write",
        "crm:read",
        "crm:write",
        "finance:read",
    ],
    "cashier": [
        "catalog:read",
        "inventory:read",
        "sales:read",
        "sales:write",
        "crm:read",
        "crm:write",
    ],
    "viewer": [
        "catalog:read",
        "inventory:read",
        "sales:read",
        "crm:read",
        "finance:read",
    ],
}
