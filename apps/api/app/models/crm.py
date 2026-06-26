"""Modelos del bounded context `crm` (clientes)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPKMixin,
)


class Customer(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_customers_document_id"),
        {"schema": "crm"},
    )

    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    document_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(CITEXT, nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Loyalty / segmentación (cacheada, recomputada por job)
    rfm_segment: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    rfm_recency_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rfm_frequency: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rfm_monetary: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    last_purchase_at: Mapped["Date | None"] = mapped_column(Date, nullable=True)  # type: ignore[name-defined]

    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Consentimiento legal Ley 1581 de 2012
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_version: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Referidos
    referral_code: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True, index=True)
    referred_by_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    referred_by_customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
