"""Contact form and newsletter subscription."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, EmailStr

from app.services.email import send_email, STORE_EMAIL

router = APIRouter(prefix="/contact", tags=["contact"])


class ContactForm(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    message: str


class NewsletterIn(BaseModel):
    email: EmailStr


@router.post("/send")
async def send_contact(payload: ContactForm, bg: BackgroundTasks) -> dict:
    """Forward contact form to store email and send auto-reply to sender."""

    def _send() -> None:
        phone_line = f"<p><strong>Teléfono:</strong> {payload.phone}</p>" if payload.phone else ""
        store_html = f"""
        <h2 style="color:#187f77;">Nuevo mensaje desde bigotesypaticas.com</h2>
        <p><strong>Nombre:</strong> {payload.name}</p>
        <p><strong>Email:</strong> {payload.email}</p>
        {phone_line}
        <hr style="border:none;border-top:1px solid #eee;margin:12px 0;">
        <p style="color:#555;">{payload.message.replace(chr(10), '<br>')}</p>
        """
        send_email(STORE_EMAIL, f"Contacto web: {payload.name}", store_html)

        first = payload.name.split()[0] if payload.name.strip() else "cliente"
        reply_html = f"""
        <h2 style="color:#187f77;">¡Hola, {first}!</h2>
        <p>Gracias por escribirnos. Recibimos tu mensaje y te responderemos a la brevedad.</p>
        <br>
        <p>Con cariño,<br><strong>El equipo de Bigotes y Paticas</strong></p>
        <p style="color:#888;font-size:12px;">
          📱 +57 320 687 6633 &nbsp;·&nbsp;
          Dosquebradas, Risaralda
        </p>
        """
        send_email(payload.email, "Recibimos tu mensaje — Bigotes y Paticas", reply_html)

    bg.add_task(_send)
    return {"ok": True}


class ReviewIn(BaseModel):
    stars: int
    comment: str | None = None
    source: str | None = "store"


@router.post("/review")
async def submit_review(payload: ReviewIn, bg: BackgroundTasks) -> dict:
    """Capture internal star rating and notify admin."""
    def _send() -> None:
        stars_txt = "⭐" * min(max(payload.stars, 1), 5)
        send_email(
            STORE_EMAIL,
            f"Nueva calificación {stars_txt} — {payload.source}",
            f"""
            <h2 style="color:#187f77;">Nueva calificación interna</h2>
            <p><strong>Estrellas:</strong> {stars_txt} ({payload.stars}/5)</p>
            <p><strong>Fuente:</strong> {payload.source}</p>
            {"<p><strong>Comentario:</strong> " + payload.comment + "</p>" if payload.comment else ""}
            """,
        )

    bg.add_task(_send)
    return {"ok": True}


@router.post("/newsletter")
async def newsletter_subscribe(payload: NewsletterIn, bg: BackgroundTasks) -> dict:
    """Log new subscriber and send welcome email."""

    def _send() -> None:
        send_email(
            STORE_EMAIL,
            f"Nueva suscripción newsletter: {payload.email}",
            f"<p>Nuevo suscriptor: <strong>{payload.email}</strong></p>",
        )
        welcome_html = """
        <h2 style="color:#187f77;">¡Bienvenido al club Bigotes y Paticas! 🐾</h2>
        <p>Gracias por suscribirte. Te enviaremos las mejores ofertas, consejos y novedades para tu mascota.</p>
        <p>Como regalo de bienvenida, usa el código
           <strong style="color:#FF6B35;font-size:18px;">BIENVENIDO10</strong>
           para obtener 10% de descuento en tu primera compra.</p>
        <br>
        <p>Con mucho cariño,<br><strong>El equipo de Bigotes y Paticas</strong></p>
        <p style="color:#888;font-size:12px;">
          📱 +57 320 687 6633 &nbsp;·&nbsp; bigotesypaticas.com
        </p>
        """
        send_email(payload.email, "¡Bienvenido al club! 10% de descuento — Bigotes y Paticas", welcome_html)

    bg.add_task(_send)
    return {"ok": True}
