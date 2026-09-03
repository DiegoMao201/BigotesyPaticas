"""Ciclo de vida unificado de la comunidad: cierre con final feliz.

Los cuatro casos (dar en adopción, buscar adoptar, mascota perdida, animal
encontrado) comparten la misma regla: al marcarse resueltos desde el admin
(o el dueño desde el portal) se exhiben como historia de éxito en el store
durante SUCCESS_PUBLIC_DAYS y después se ocultan solos -- no hay cron: las
consultas públicas filtran por `public_until > now()`.

Este módulo concentra los textos para que el store, el sitemap y el JSON-LD
digan siempre lo mismo.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import UTC, datetime, timedelta

SUCCESS_PUBLIC_DAYS = 30

STORE_BASE = "https://bigotesypaticas.com"
STORE_PATHS = {
    "adoption": "/adopcion",
    "lost": "/mascotas-perdidas",
    "found": "/mascotas-encontradas",
}
SUCCESS_PAGE_URL = f"{STORE_BASE}/finales-felices"


def public_window(resolved_at: datetime | None = None) -> tuple[datetime, datetime]:
    """(resolved_at, public_until) para una resolución que ocurre ahora."""
    at = resolved_at or datetime.now(UTC)
    return at, at + timedelta(days=SUCCESS_PUBLIC_DAYS)


def is_publicly_visible(public_until: datetime | None) -> bool:
    return public_until is not None and public_until > datetime.now(UTC)


# ── Textos de final feliz ─────────────────────────────────────────────


def lost_headline(pet_name: str) -> str:
    return f"¡{pet_name} ya está en casa! 🎉"


def lost_default_note(pet_name: str) -> str:
    return (
        f"Gracias a todos los que compartieron y estuvieron pendientes: "
        f"{pet_name} volvió a su hogar. 💛"
    )


def found_headline() -> str:
    return "¡Reunidos con su familia! 🎉"


def found_default_note(title: str) -> str:
    return f"Gracias a la comunidad, {title} ya está de vuelta con su familia. 💛"


def adoption_headline(post_type: str) -> str:
    return "¡Ya adoptó! 🎉" if post_type == "want" else "¡Encontró un hogar! 🎉"


def adoption_default_note(post_type: str) -> str:
    if post_type == "want":
        return "Ya encontró a su nuevo peludito gracias a la comunidad de Bigotes y Paticas. 💛"
    return "Encontró una familia gracias a la comunidad de Bigotes y Paticas. 💛"


def resolved_urls(entity_type: str, entity_id) -> list[str]:
    """URLs a avisar a IndexNow cuando cambia el estado de una publicación."""
    path = STORE_PATHS[entity_type]
    return [
        f"{STORE_BASE}{path}",
        f"{STORE_BASE}{path}/{entity_id}",
        SUCCESS_PAGE_URL,
        f"{STORE_BASE}/sitemap.xml",
    ]


# ── Comentarios públicos ──────────────────────────────────────────────

COMMENT_MIN_LEN = 2
COMMENT_MAX_LEN = 500
COMMENT_NAME_MAX_LEN = 80
COMMENTS_PER_IP_PER_ENTITY_PER_DAY = 5
COMMENTS_PER_IP_PER_DAY = 30

_URL_RE = re.compile(r"(https?://|www\.)", re.IGNORECASE)


def hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    salt = os.environ.get("SECRET_KEY", "bigotesypaticas")
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()


def clean_comment(author_name: str, body: str) -> tuple[str, str, str | None]:
    """Devuelve (nombre, texto, error). Sin enlaces: es la forma más simple
    y efectiva de cortar el spam en un formulario público sin cuenta."""
    name = re.sub(r"\s+", " ", author_name).strip()[:COMMENT_NAME_MAX_LEN]
    text = re.sub(r"[ \t]+", " ", body).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(name) < 2:
        return name, text, "Escribe tu nombre"
    if len(text) < COMMENT_MIN_LEN:
        return name, text, "El comentario está vacío"
    if len(text) > COMMENT_MAX_LEN:
        return name, text, f"Máximo {COMMENT_MAX_LEN} caracteres"
    if _URL_RE.search(text) or _URL_RE.search(name):
        return name, text, "Los comentarios no pueden incluir enlaces"
    return name, text, None
