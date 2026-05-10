"""Seed inicial: crea roles canónicos, admin user, location default.

Idempotente. Ejecutar tras `alembic upgrade head`.
    python -m app.cli.seed
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.models.auth import ROLE_DEFAULTS, Role, User
from app.models.inventory import StockLocation
from app.security import hash_password


async def seed() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        # --- Roles
        for name, perms in ROLE_DEFAULTS.items():
            existing = (
                await db.execute(select(Role).where(Role.name == name))
            ).scalar_one_or_none()
            if existing is None:
                db.add(Role(name=name, description=f"Rol {name}", permissions=perms))
                print(f"  + role: {name}")
            else:
                # actualizar permisos si cambiaron
                if set(existing.permissions or []) != set(perms):
                    existing.permissions = perms
                    print(f"  ~ role updated: {name}")
        await db.commit()

        # --- Superadmin
        superadmin_role = (
            await db.execute(select(Role).where(Role.name == "superadmin"))
        ).scalar_one()
        admin = (
            await db.execute(select(User).where(User.email == settings.admin_email))
        ).scalar_one_or_none()
        if admin is None:
            admin = User(
                email=settings.admin_email,
                full_name="Administrador",
                password_hash=hash_password(settings.admin_password),
                is_active=True,
                is_superadmin=True,
            )
            admin.roles.append(superadmin_role)
            db.add(admin)
            print(f"  + superadmin: {settings.admin_email}")
        else:
            if superadmin_role not in admin.roles:
                admin.roles.append(superadmin_role)
            admin.is_superadmin = True
            print(f"  ~ superadmin OK: {settings.admin_email}")

        # --- Stock location default
        loc = (
            await db.execute(select(StockLocation).where(StockLocation.code == "MAIN"))
        ).scalar_one_or_none()
        if loc is None:
            db.add(StockLocation(code="MAIN", name="Tienda principal", is_default=1))
            print("  + location MAIN")

        await db.commit()
        print("Seed completado.")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
