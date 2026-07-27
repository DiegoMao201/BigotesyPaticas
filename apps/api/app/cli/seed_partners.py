"""Seed demo del directorio de aliados (Fase 3). Idempotente — no pisa datos
reales cuando el usuario empiece a cargar aliados de verdad (el check es
por slug, y estos slugs demo no colisionan con negocios reales).

    python -m app.cli.seed_partners
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.partners import Partner, Service

PARTNERS = [
    {
        "slug": "veterinaria-huellitas-pereira",
        "partner_type": "vet",
        "business_name": "Veterinaria Huellitas",
        "legal_name": "Huellitas Veterinaria S.A.S.",
        "document_id": "900111222-1",
        "phone": "3201234567",
        "whatsapp": "3201234567",
        "address": "Cra 8 # 23-45",
        "city": "Pereira",
        "bio": "Consulta general, vacunación y cirugía. Más de 10 años cuidando mascotas en Pereira.",
        "verified": True,
        "services": [
            {
                "slug": "consulta-general",
                "name": "Consulta general",
                "category": "consulta",
                "price": Decimal("45000"),
                "price_type": "fixed",
                "duration_min": 30,
            },
            {
                "slug": "vacunacion",
                "name": "Vacunación",
                "category": "vacunacion",
                "price": Decimal("60000"),
                "price_type": "from",
                "duration_min": 20,
            },
        ],
    },
    {
        "slug": "clinica-veterinaria-patitas-dosquebradas",
        "partner_type": "vet",
        "business_name": "Clínica Veterinaria Patitas",
        "legal_name": "Patitas Clínica Veterinaria Ltda.",
        "document_id": "900222333-2",
        "phone": "3157654321",
        "whatsapp": "3157654321",
        "address": "Calle 10 # 5-20",
        "city": "Dosquebradas",
        "bio": "Atención veterinaria integral: consulta, esterilización y odontología.",
        "verified": False,
        "services": [
            {
                "slug": "esterilizacion",
                "name": "Esterilización",
                "category": "esterilizacion",
                "price": Decimal("180000"),
                "price_type": "from",
                "duration_min": 90,
            },
            {
                "slug": "consulta-general",
                "name": "Consulta general",
                "category": "consulta",
                "price": Decimal("40000"),
                "price_type": "fixed",
                "duration_min": 30,
            },
        ],
    },
    {
        "slug": "paseos-felices-pereira",
        "partner_type": "walker",
        "business_name": "Paseos Felices",
        "legal_name": "Paseos Felices S.A.S.",
        "document_id": "900333444-3",
        "phone": "3109876543",
        "whatsapp": "3109876543",
        "address": "Av. Circunvalar",
        "city": "Pereira",
        "bio": "Paseadores certificados, rutas seguras y fotos de cada paseo.",
        "verified": True,
        "services": [
            {
                "slug": "paseo-30min",
                "name": "Paseo 30 min",
                "category": "paseo_30min",
                "price": Decimal("18000"),
                "price_type": "fixed",
                "duration_min": 30,
            },
            {
                "slug": "paseo-60min",
                "name": "Paseo 60 min",
                "category": "paseo_60min",
                "price": Decimal("30000"),
                "price_type": "fixed",
                "duration_min": 60,
            },
        ],
    },
    {
        "slug": "walker-pro-dosquebradas",
        "partner_type": "walker",
        "business_name": "Walker Pro",
        "legal_name": "Walker Pro Servicios",
        "document_id": "900444555-4",
        "phone": "3123456789",
        "whatsapp": "3123456789",
        "address": "Barrio La Popa",
        "city": "Dosquebradas",
        "bio": "Paseos individuales y grupales, disponibilidad mañana y tarde.",
        "verified": False,
        "services": [
            {
                "slug": "paseo-30min",
                "name": "Paseo 30 min",
                "category": "paseo_30min",
                "price": Decimal("15000"),
                "price_type": "fixed",
                "duration_min": 30,
            },
        ],
    },
    {
        "slug": "refugio-huellas-de-esperanza",
        "partner_type": "shelter",
        "business_name": "Refugio Huellas de Esperanza",
        "legal_name": "Fundación Huellas de Esperanza",
        "document_id": "900555666-5",
        "phone": "3134567890",
        "whatsapp": "3134567890",
        "address": "Vereda La Bella, km 3",
        "city": "Pereira",
        "bio": "Fundación de rescate y adopción responsable de perros y gatos.",
        "verified": True,
        "services": [
            {
                "slug": "asesoria-adopcion",
                "name": "Asesoría de adopción",
                "category": "consulta",
                "price": None,
                "price_type": "quote",
                "duration_min": None,
                "requires_pet": False,
            },
        ],
    },
    {
        "slug": "fundacion-patitas-libres",
        "partner_type": "shelter",
        "business_name": "Fundación Patitas Libres",
        "legal_name": "Fundación Patitas Libres",
        "document_id": "900666777-6",
        "phone": "3145678901",
        "whatsapp": "3145678901",
        "address": "Sector El Poblado",
        "city": "Dosquebradas",
        "bio": "Rescate, esterilización y adopción de animales en situación de calle.",
        "verified": False,
        "services": [
            {
                "slug": "asesoria-adopcion",
                "name": "Asesoría de adopción",
                "category": "consulta",
                "price": None,
                "price_type": "quote",
                "duration_min": None,
                "requires_pet": False,
            },
        ],
    },
    {
        "slug": "estetica-canina-glamour-pet",
        "partner_type": "groomer",
        "business_name": "Glamour Pet Spa",
        "legal_name": "Glamour Pet S.A.S.",
        "document_id": "900777888-7",
        "phone": "3167890123",
        "whatsapp": "3167890123",
        "address": "Centro Comercial Victoria",
        "city": "Pereira",
        "bio": "Baño, corte y spa canino con productos hipoalergénicos.",
        "verified": True,
        "services": [
            {
                "slug": "bano-completo",
                "name": "Baño completo",
                "category": "bano",
                "price": Decimal("35000"),
                "price_type": "from",
                "duration_min": 60,
            },
            {
                "slug": "corte",
                "name": "Corte de pelo",
                "category": "corte",
                "price": Decimal("45000"),
                "price_type": "from",
                "duration_min": 60,
            },
        ],
    },
    {
        "slug": "peluqueria-canina-pelusa",
        "partner_type": "groomer",
        "business_name": "Peluquería Canina Pelusa",
        "legal_name": "Pelusa Estética Animal",
        "document_id": "900888999-8",
        "phone": "3178901234",
        "whatsapp": "3178901234",
        "address": "Barrio Frailes",
        "city": "Dosquebradas",
        "bio": "Baño y corte para perros y gatos de todos los tamaños.",
        "verified": False,
        "services": [
            {
                "slug": "bano-completo",
                "name": "Baño completo",
                "category": "bano",
                "price": Decimal("30000"),
                "price_type": "fixed",
                "duration_min": 45,
            },
        ],
    },
]


async def seed_partners() -> None:
    async with AsyncSessionLocal() as db:
        for data in PARTNERS:
            data = dict(data)
            services = data.pop("services")
            verified = data.pop("verified")

            existing = (
                await db.execute(select(Partner).where(Partner.slug == data["slug"]))
            ).scalar_one_or_none()
            if existing is not None:
                continue

            partner = Partner(
                **data,
                published_at=datetime.now(UTC),
                verified_at=datetime.now(UTC) if verified else None,
            )
            db.add(partner)
            await db.flush()

            for svc in services:
                db.add(Service(partner_id=partner.id, **svc))

            print(f"  + partner: {data['business_name']}")

        await db.commit()
        print("Seed de aliados completado.")


def main() -> None:
    asyncio.run(seed_partners())


if __name__ == "__main__":
    main()
