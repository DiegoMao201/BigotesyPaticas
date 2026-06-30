"""Endpoints de clientes (CRM básico)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.deps import DBSession, require_permission
from app.models.crm import Customer
from app.models.sales import Order

router = APIRouter(prefix="/customers", tags=["customers"])


class CustomerOut(BaseModel):
    id: str
    full_name: str
    document_id: str | None
    email: str | None
    phone: str | None
    address: str | None
    city: str | None
    notes: str | None
    pet_name: str | None
    pet_type: str | None
    pet_notes: str | None
    pet_birthday: str | None
    last_deworming: str | None
    rfm_segment: str | None
    rfm_monetary: float | None
    last_purchase_at: str | None
    created_at: str

    @classmethod
    def from_orm(cls, c: Customer) -> CustomerOut:
        extra = c.extra or {}
        return cls(
            id=str(c.id),
            full_name=c.full_name,
            document_id=c.document_id,
            email=c.email,
            phone=c.phone,
            address=c.address,
            city=c.city,
            notes=c.notes,
            pet_name=extra.get("pet_name"),
            pet_type=extra.get("pet_type"),
            pet_notes=extra.get("pet_notes"),
            pet_birthday=extra.get("pet_birthday"),
            last_deworming=extra.get("last_deworming"),
            rfm_segment=c.rfm_segment,
            rfm_monetary=float(c.rfm_monetary) if c.rfm_monetary else None,
            last_purchase_at=str(c.last_purchase_at) if c.last_purchase_at else None,
            created_at=c.created_at.isoformat(),
        )


class CustomerCreate(BaseModel):
    full_name: str
    document_id: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    notes: str | None = None
    pet_name: str | None = None
    pet_type: str | None = None
    pet_notes: str | None = None
    pet_birthday: str | None = None
    last_deworming: str | None = None


class PaginatedCustomers(BaseModel):
    items: list[CustomerOut]
    total: int
    page: int
    page_size: int


@router.get(
    "",
    response_model=PaginatedCustomers,
    dependencies=[Depends(require_permission("crm:read"))],
)
async def list_customers(
    db: DBSession,
    q: str | None = Query(None, description="Nombre, email, teléfono o documento"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedCustomers:
    stmt = select(Customer).where(Customer.deleted_at == None)  # noqa: E711
    if q:
        term = f"%{q}%"
        stmt = stmt.where(
            or_(
                Customer.full_name.ilike(term),
                Customer.email.ilike(term),
                Customer.phone.ilike(term),
                Customer.document_id.ilike(term),
            )
        )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        (
            await db.execute(
                stmt.order_by(Customer.full_name).offset((page - 1) * page_size).limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return PaginatedCustomers(
        items=[CustomerOut.from_orm(c) for c in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerOut,
    dependencies=[Depends(require_permission("crm:read"))],
)
async def get_customer(customer_id: uuid.UUID, db: DBSession) -> CustomerOut:
    c = (
        await db.execute(
            select(Customer).where(Customer.id == customer_id).where(Customer.deleted_at == None)  # noqa: E711
        )
    ).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return CustomerOut.from_orm(c)


@router.post(
    "",
    response_model=CustomerOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("crm:write"))],
)
async def create_customer(payload: CustomerCreate, db: DBSession) -> CustomerOut:
    extra: dict[str, str] = {}
    if payload.pet_name:
        extra["pet_name"] = payload.pet_name
    if payload.pet_type:
        extra["pet_type"] = payload.pet_type
    if payload.pet_notes:
        extra["pet_notes"] = payload.pet_notes
    if payload.pet_birthday:
        extra["pet_birthday"] = payload.pet_birthday
    if payload.last_deworming:
        extra["last_deworming"] = payload.last_deworming

    c = Customer(
        full_name=payload.full_name,
        document_id=payload.document_id,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        city=payload.city,
        notes=payload.notes,
        extra=extra,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return CustomerOut.from_orm(c)


class CustomerUpdate(BaseModel):
    full_name: str | None = None
    document_id: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    notes: str | None = None
    pet_name: str | None = None
    pet_type: str | None = None
    pet_notes: str | None = None
    pet_birthday: str | None = None
    last_deworming: str | None = None


@router.patch(
    "/{customer_id}",
    response_model=CustomerOut,
    dependencies=[Depends(require_permission("crm:write"))],
)
async def update_customer(
    customer_id: uuid.UUID, payload: CustomerUpdate, db: DBSession
) -> CustomerOut:
    c = (
        await db.execute(
            select(Customer).where(Customer.id == customer_id).where(Customer.deleted_at == None)  # noqa: E711
        )
    ).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    data = payload.model_dump(exclude_unset=True)
    extra = dict(c.extra or {})

    for key in ["pet_name", "pet_type", "pet_notes", "pet_birthday", "last_deworming"]:
        if key in data:
            value = data.pop(key)
            if value:
                extra[key] = value
            else:
                extra.pop(key, None)

    for k, v in data.items():
        setattr(c, k, v)

    c.extra = extra
    await db.commit()
    await db.refresh(c)
    return CustomerOut.from_orm(c)


@router.get(
    "/{customer_id}/orders",
    dependencies=[Depends(require_permission("crm:read"))],
)
async def customer_orders(customer_id: uuid.UUID, db: DBSession) -> list[dict]:
    orders = (
        (
            await db.execute(
                select(Order)
                .where(Order.customer_id == customer_id)
                .order_by(Order.occurred_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(o.id),
            "order_number": o.order_number,
            "status": o.status,
            "grand_total": float(o.grand_total),
            "payment_status": o.payment_status,
            "occurred_at": o.occurred_at.isoformat(),
        }
        for o in orders
    ]
