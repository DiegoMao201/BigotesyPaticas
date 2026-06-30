#!/usr/bin/env python3
"""
Backfill: Crea sales.orders para portal_orders delivered que no tienen sales_order_id.

INSTRUCCIONES:
  1. Revisar la lista de pedidos candidatos (ver MISIÓN 4.1 del reporte)
  2. Confirmar con Diego qué IDs incluir
  3. Ejecutar CON la lista de IDs confirmados:

     python scripts/backfill_portal_to_sales.py \
       --order-ids ff41392c-1727-459c-9028-883d41a126b2 \
                   06fc7471-0aee-4aa0-8034-361e909b9d80

  4. Sin --order-ids, el script solo lista los candidatos (modo dry-run implícito).

SEGURIDAD:
  - Idempotente: si el pedido ya tiene sales_order_id, lo omite.
  - No otorga puntos retroactivos si points_awarded ya > 0.
  - No procesa referidos si reward_paid_at ya fue seteado.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from collections.abc import Sequence

# Ruta base del proyecto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def main(order_ids: Sequence[str]) -> None:
    from app.models.crm import Customer
    from app.models.portal import PortalOrder, PortalOrderItem
    from app.services.portal_order_actions import (
        bridge_to_sales,
        credit_loyalty_points,
        process_referral_reward,
    )
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL no definida.")
        sys.exit(1)

    engine = create_async_engine(db_url, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        if not order_ids:
            print("\n=== CANDIDATOS PARA BACKFILL ===")
            print("(portal_orders delivered SIN sales_order_id)\n")
            rows = (
                (
                    await db.execute(
                        select(PortalOrder)
                        .where(
                            PortalOrder.workflow_status == "delivered",
                            PortalOrder.sales_order_id == None,  # noqa: E711
                        )
                        .order_by(PortalOrder.delivered_at.desc())
                    )
                )
                .scalars()
                .all()
            )

            if not rows:
                print("No hay pedidos pendientes de backfill.")
                return

            for o in rows:
                c = (
                    await db.execute(select(Customer).where(Customer.id == o.customer_id))
                ).scalar_one_or_none()
                items = (
                    (
                        await db.execute(
                            select(PortalOrderItem).where(
                                PortalOrderItem.portal_order_id == o.id,
                                PortalOrderItem.is_removed == False,  # noqa: E712
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                total = sum(float(i.subtotal or 0) for i in items)
                if not total and o.unit_price:
                    total = float(o.unit_price) * (o.quantity or 1)

                print(
                    f"  ID: {o.id}\n"
                    f"  Cliente: {c.full_name if c else '?'} | Tel: {c.phone if c else '?'}\n"
                    f"  Entregado: {o.delivered_at}\n"
                    f"  Total: ${total:,.0f} COP\n"
                    f"  Puntos acreditados ya: {o.points_awarded}\n"
                    f"  Productos: {', '.join(i.name or '?' for i in items)}\n"
                )

            print(
                f"Total: {len(rows)} pedido(s) candidato(s).\n\n"
                "Para ejecutar backfill:\n"
                "  python scripts/backfill_portal_to_sales.py --order-ids <id1> <id2> ...\n"
            )
            return

        # Modo backfill real
        print(f"\n=== BACKFILL REAL — {len(order_ids)} pedido(s) ===\n")
        processed = 0
        skipped = 0
        errors = []

        for raw_id in order_ids:
            try:
                oid = uuid.UUID(raw_id)
                order = (
                    await db.execute(select(PortalOrder).where(PortalOrder.id == oid))
                ).scalar_one_or_none()

                if not order:
                    print(f"  ⚠️  {raw_id}: No encontrado")
                    skipped += 1
                    continue

                if order.sales_order_id:
                    print(
                        f"  ⏭  {raw_id}: Ya tiene sales_order_id={order.sales_order_id} — omitido"
                    )
                    skipped += 1
                    continue

                if order.workflow_status != "delivered":
                    print(
                        f"  ⚠️  {raw_id}: workflow_status={order.workflow_status}, esperado 'delivered' — omitido"
                    )
                    skipped += 1
                    continue

                invoice_num = await bridge_to_sales(order, db)
                pts = await credit_loyalty_points(order, db)
                got_referral = await process_referral_reward(order, db)

                await db.commit()
                print(
                    f"  ✅ {raw_id}: invoice={invoice_num}, "
                    f"puntos={pts}, referido={'sí' if got_referral else 'no'}"
                )
                processed += 1

            except Exception as exc:
                await db.rollback()
                print(f"  ❌ {raw_id}: ERROR — {exc}")
                errors.append(raw_id)

    print(
        f"\n=== RESUMEN ===\n"
        f"  Procesados: {processed}\n"
        f"  Omitidos:   {skipped}\n"
        f"  Errores:    {len(errors)}"
    )
    if errors:
        print(f"  IDs con error: {errors}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backfill portal → sales bridge")
    parser.add_argument(
        "--order-ids",
        nargs="*",
        default=[],
        help="UUIDs de portal_orders a backfillear. Sin argumentos: lista candidatos.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.order_ids))
