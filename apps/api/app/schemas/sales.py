"""Schemas Pydantic v2 — sales."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderItemIn(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)
    unit_price: Decimal | None = None  # si no se da, toma price del producto
    discount: Decimal = Decimal("0")


class PaymentIn(BaseModel):
    method: str = Field(min_length=1, max_length=40)
    amount: Decimal = Field(gt=0)
    reference: str | None = None
    notes: str | None = None


class OrderCreate(BaseModel):
    customer_id: uuid.UUID | None = None
    channel: str = "POS_NEW"
    items: list[OrderItemIn] = Field(min_length=1)
    payments: list[PaymentIn] = []
    shipping_total: Decimal = Decimal("0")
    notes: str | None = None
    occurred_at: datetime | None = None  # si None → now()


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    sku_snapshot: str
    name_snapshot: str
    quantity: int
    unit_price: Decimal
    unit_cost: Decimal
    discount: Decimal
    line_total: Decimal


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    method: str
    amount: Decimal
    received_at: datetime
    reference: str | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    order_number: str
    channel: str
    status: str
    customer_id: uuid.UUID | None = None
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    shipping_total: Decimal
    grand_total: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    payment_status: str
    payment_method: str | None = None
    occurred_at: datetime
    notes: str | None = None
    items: list[OrderItemOut] = []
    payments: list[PaymentOut] = []
