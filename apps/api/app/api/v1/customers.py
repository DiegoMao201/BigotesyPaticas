"""Endpoints de clientes (CRM básico)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.deps import CurrentUser, DBSession, require_permission
from app.models.crm import Customer
from app.models.sales import Order

router = APIRouter(prefix="/customers", tags=["customers"])


class CustomerOut(BaseModel):
    id: str
    full_name: str
    document_id: str | None
    email: str | None
    phone: str | None
    city: str | None
    rfm_segment: str | None
    rfm_monetary: float | None
    last_purchase_at: str | None
    created_at: str

    @classmethod
    def from_orm(cls, c: Customer) -> "CustomerOut":
        return cls(
            id=str(c.id),
            full_name=c.full_name,
            document_id=c.document_id,
            email=c.email,
            phone=c.phone,
            city=c.city,
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
        await db.execute(
            stmt.order_by(Customer.full_name).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
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
            select(Customer)
            .where(Customer.id == customer_id)
            .where(Customer.deleted_at == None)  # noqa: E711
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
    c = Customer(
        full_name=payload.full_name,
        document_id=payload.document_id,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        city=payload.city,
        notes=payload.notes,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return CustomerOut.from_orm(c)


@router.get(
    "/{customer_id}/orders",
    dependencies=[Depends(require_permission("crm:read"))],
)
async def customer_orders(customer_id: uuid.UUID, db: DBSession) -> list[dict]:
    orders = (
        await db.execute(
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.occurred_at.desc())
            .limit(50)
        )
    ).scalars().all()
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
