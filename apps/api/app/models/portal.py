"""Modelos del schema `portal` — App de Fidelización de Clientes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    func,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.crm import Customer


class Pet(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "pets"
    __table_args__ = (
        CheckConstraint(
            "color_theme IN ('teal','coral','amber','purple','pink','green')",
            name="ck_pets_color_theme",
        ),
        {"schema": "portal"},
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    breed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    birth_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    food_brand: Mapped[str | None] = mapped_column(String(200), nullable=True)
    food_freq_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color_theme: Mapped[str] = mapped_column(String(20), nullable=False, default="teal")
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, index=True
    )
    is_lost: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    health_records: Mapped[list[HealthRecord]] = relationship(
        "HealthRecord", back_populates="pet", cascade="all, delete-orphan", lazy="selectin"
    )
    appointments: Mapped[list[Appointment]] = relationship(
        "Appointment", back_populates="pet", cascade="all, delete-orphan"
    )


class HealthRecord(UUIDPKMixin, Base):
    __tablename__ = "health_records"
    __table_args__ = ({"schema": "portal"},)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    pet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portal.pets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    record_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(Date, nullable=False)
    next_due_at: Mapped[datetime | None] = mapped_column(Date, nullable=True, index=True)
    vet_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    pet: Mapped[Pet] = relationship("Pet", back_populates="health_records")


class AgendaBloqueo(UUIDPKMixin, TimestampMixin, Base):
    """Días u horas sin atención de peluquería (vacaciones, groomer enfermo…). La web y
    el portal no ofrecen horas que se crucen; el admin sí puede agendar encima."""

    __tablename__ = "agenda_bloqueos"
    __table_args__ = ({"schema": "portal"},)

    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Appointment(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','confirmed','completed','cancelled')",
            name="ck_appt_status",
        ),
        {"schema": "portal"},
    )

    pet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portal.pets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_type: Mapped[str] = mapped_column(String(100), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sprint-2 (reagendamiento) -- columnas reales desde la migración 0014,
    # antes no estaban mapeadas en el ORM y los `hasattr()` que las usaban
    # siempre daban False, perdiendo el motivo/puntos del reagendamiento.
    workflow_status: Mapped[str | None] = mapped_column(
        String(40), nullable=True, default="requested"
    )
    rescheduled_from_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reschedule_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reschedule_reason_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    compensation_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    proposed_options: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Google (2-oct-2026). La reserva en la web ya se reporta como lead; la VENTA se
    # reporta cuando el admin completa la cita y escribe cuánto cobró (price). El
    # client_id de la cookie _ga es lo que permite atribuir esa venta a la búsqueda o
    # al anuncio que trajo al cliente; sin él entraría como "(direct)".
    origen: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ga_client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ga_session_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gclid: Mapped[str | None] = mapped_column(Text, nullable=True)
    purchase_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pet: Mapped[Pet] = relationship("Pet", back_populates="appointments")


class PortalOrder(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "portal_orders"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_portal_orders_qty"),
        CheckConstraint(
            "status IN ('received','processing','invoiced','ready','delivered','cancelled')",
            name="ck_portal_order_status",
        ),
        {"schema": "portal"},
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portal.pets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.products.id", ondelete="SET NULL"),
        nullable=True,
    )
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="received", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # v4 columns
    invoice_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    invoiced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invoice_pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    under_minimum: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sales_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shipping_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    # sprint-2 workflow
    workflow_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="received", index=True
    )
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_facing_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_status_change_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_status_changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    customer_confirmed_changes_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    customer_confirmation_channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0")
    )
    discount_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    # Pedidos de la tienda web (2-oct-2026). 'origen' distingue el canal; el client_id
    # de la cookie _ga es lo que le permite a GA4 pegar la compra con la búsqueda o el
    # anuncio que trajo al cliente — sin él la venta queda como "(direct)".
    origen: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    ga_client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ga_session_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gclid: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Pago en línea con Bold (4-oct-2026). El pago es un ESTADO MÁS de este pedido,
    # no un pedido distinto: así hereda el puente a sales, los puntos, las
    # notificaciones y la vista del admin que ya funcionan. Ver la migración 0046.
    #
    # `payment_method` ya existía arriba y en producción vale 'cash', 'transfer' o
    # 'nequi'. Se le suma 'bold' en minúscula, para no partir el vocabulario en dos.
    #
    # `bold_amount` es el entero EXACTO que se firmó y se le mandó a Bold: pesos sin
    # decimales ni separadores (76000, nunca 76.000 ni 76000.00). Va aparte de
    # `total_amount` porque es el valor contra el que se compara lo que devuelve el
    # webhook; recalcularlo desde el Numeric al validar arriesga que un redondeo
    # distinto nos haga rechazar un pago bueno.
    order_reference: Mapped[str | None] = mapped_column(String(60), nullable=True)
    payment_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bold_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    bold_payment_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    purchase_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # ── Antifraude (8-oct-2026, migración 0049) ──────────────────────────────
    # Bold manda estos datos en cada evento y hasta hoy morían dentro de
    # `raw_payload`. Van a columnas porque lo que delata un fraude es poder cruzar:
    # la misma tarjeta en dos clientes distintos, tres tarjetas en un mismo teléfono.
    # Una señal que no se puede consultar con un WHERE no detecta nada.
    bold_payment_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    bold_card_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bold_card_brand: Mapped[str | None] = mapped_column(String(40), nullable=True)
    bold_masked_pan: Mapped[str | None] = mapped_column(String(25), nullable=True)
    bold_payer_email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    bold_integration: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bold_installments: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    # El veredicto del semáforo. Se guarda en vez de recalcularse para que el admin
    # lo vea sin trabajo y para poder medir después si acierta.
    risk_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    risk_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    risk_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    risk_cleared_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    risk_cleared_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    risk_cleared_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Con qué se defiende una disputa. Bold dice que lo que la gana son "guías de
    # envío, fotos del producto recibido, soportes de entrega". Vacío = perdida.
    delivered_to_name: Mapped[str | None] = mapped_column(String(140), nullable=True)
    delivered_to_doc: Mapped[str | None] = mapped_column(String(40), nullable=True)
    delivery_evidence_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PortalOrderItem(UUIDPKMixin, Base):
    __tablename__ = "portal_order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_portal_order_items_qty"),
        {"schema": "portal"},
    )

    portal_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portal.portal_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.products.id", ondelete="SET NULL"),
        nullable=True,
    )
    sku: Mapped[str | None] = mapped_column(String(120), nullable=True)
    name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_substituted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    substituted_from_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_removed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )


class ActivityLog(Base):
    __tablename__ = "activity_log"
    __table_args__ = ({"schema": "portal"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    visible_to_customer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notification_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notification_channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )


class PortalSession(UUIDPKMixin, Base):
    __tablename__ = "portal_sessions"
    __table_args__ = ({"schema": "portal"},)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class LoyaltyPoint(UUIDPKMixin, Base):
    __tablename__ = "loyalty_points"
    __table_args__ = (
        CheckConstraint("points <> 0", name="ck_loyalty_points_positive"),
        CheckConstraint(
            "reason IN ('purchase','portal_order','appointment','referral','manual')",
            name="ck_loyalty_reason",
        ),
        {"schema": "portal"},
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PortalNotification(UUIDPKMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "type IN ('health_reminder','order_update','loyalty','appointment','birthday','general',"
            "'new_order','new_appointment','new_customer','order_confirmed','order_ready',"
            "'order_delivered','appt_confirmed','appt_rescheduled','appt_cancelled',"
            "'referral_signup','referral_reward','welcome_bonus','order_invoiced')",
            name="ck_notif_type",
        ),
        {"schema": "portal"},
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    action_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class PendingNotification(UUIDPKMixin, Base):
    __tablename__ = "pending_notifications"
    __table_args__ = ({"schema": "portal"},)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    portal_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portal.portal_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_code: Mapped[str] = mapped_column(String(80), nullable=False)
    rendered_message: Mapped[str] = mapped_column(Text, nullable=False)
    whatsapp_link: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class PortalReferral(Base):
    __tablename__ = "referrals"
    __table_args__: ClassVar[dict] = {"schema": "portal"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referrer_customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referred_customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm.customers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    referral_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    signed_up_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    first_purchase_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reward_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    referrer: Mapped[Customer] = relationship(  # type: ignore[name-defined]
        "Customer", foreign_keys=[referrer_customer_id]
    )
    referred: Mapped[Customer] = relationship(  # type: ignore[name-defined]
        "Customer", foreign_keys=[referred_customer_id]
    )


class PaymentEvent(UUIDPKMixin, Base):
    """Bitácora de todo lo que llega de Bold, válido o no.

    Hace tres trabajos y por eso vale una tabla propia:

    1. **Idempotencia.** `bold_payment_id` es UNIQUE, así que el procesamiento
       empieza con `INSERT ... ON CONFLICT DO NOTHING`: si no insertó nada, ese pago
       ya se procesó y se responde 200 sin tocar el pedido. Bold reintenta el webhook
       hasta cinco veces (15 min, 1 h, 4 h, 8 h, 24 h) y esos reintentos son
       funcionamiento normal, no un error. El candado vive en la base y no en una
       comprobación previa, que es lo que lo hace resistir dos reintentos a la vez.
    2. **Auditoría.** Una discrepancia entre lo que cobró Bold y lo que guardamos
       queda escrita con su `raw_payload`, que es la única forma de investigarla.
    3. **Depuración.** Los intentos con firma inválida se guardan IGUAL, con
       `signature_valid = False`. Sin eso, una integración que falla por la firma
       obliga a reproducir el pago para poder verla.
    """

    __tablename__ = "payment_events"
    __table_args__: ClassVar = {"schema": "portal"}

    bold_payment_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    order_reference: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    signature_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class Chargeback(UUIDPKMixin, Base):
    """Un contracargo que llegó: la plata que Bold va a debitar si perdemos la disputa.

    **Esta tabla se llena A MANO, y no es un descuido.** El webhook de Bold tiene
    cuatro eventos —`SALE_APPROVED`, `SALE_REJECTED`, `VOID_APPROVED`,
    `VOID_REJECTED`— y **ninguno es de contracargo**: Bold avisa de la disputa por
    correo, así que el sistema no puede enterarse solo. Si no se registra aquí, no
    existe en ninguna parte y no hay forma de saber cómo vamos.

    Y hay que saberlo, por dos razones con fecha: Bold da **2 días hábiles** para
    mandar los soportes y debita **dentro de los 3 días hábiles** siguientes a su
    aviso. Un contracargo que nadie anotó es un contracargo que vence solo.

    La tercera razón es el **2,5 %**: ese es el índice de fraude máximo que Bold
    tolera antes de poder retener saldos. Sin este registro no hay denominador.
    """

    __tablename__ = "chargebacks"
    __table_args__ = (
        CheckConstraint("outcome IN ('pendiente','ganado','perdido')", name="ck_chargeback_outcome"),
        CheckConstraint("amount > 0", name="ck_chargeback_amount"),
        {"schema": "portal"},
    )

    order_reference: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    bold_payment_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: 2 días hábiles desde el aviso. Es LA fecha que importa: pasada, no hay nada que hacer.
    evidence_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evidence_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evidence_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PaymentApplication(UUIDPKMixin, Base):
    """A qué venta (o ventas) se le aplicó un pago sin pedido.

    Diego (9-oct-2026): *"puede ser una o dos ventas o muchas ventas un solo pago"*.
    Una fila por (pago, venta), con **cuánto se le abonó a cada una**: un pago de
    $500.000 repartido entre tres facturas no es lo mismo que tres pagos de $500.000.

    `amount` puede ser **0**, y es un caso normal, no un error: la venta ya estaba
    cobrada —se registró el pago al facturar— y lo único que aporta esta fila es la
    trazabilidad, o sea poder responder *"¿qué pago cubrió esta venta?"* cuando llegue
    un contracargo.
    """

    __tablename__ = "payment_applications"
    __table_args__ = (
        UniqueConstraint("portal_order_id", "sales_order_id", name="uq_pago_venta"),
        CheckConstraint("amount >= 0", name="ck_pago_venta_monto"),
        {"schema": "portal"},
    )

    portal_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sales_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sales_payment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    #: GA4 se marca POR VENTA: si el pago cubre tres facturas son tres transacciones
    #: distintas para Google, y aplicarlas en dos tandas no puede dejar fuera a nadie.
    purchase_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[str | None] = mapped_column(String(150), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
