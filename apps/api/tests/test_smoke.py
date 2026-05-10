"""Smoke tests que NO requieren base de datos (no I/O)."""
from __future__ import annotations


def test_password_hash_roundtrip() -> None:
    from app.security import hash_password, verify_password

    h = hash_password("MiPassword123!")
    assert h != "MiPassword123!"
    assert verify_password("MiPassword123!", h)
    assert not verify_password("otro", h)


def test_jwt_roundtrip() -> None:
    from app.security import create_access_token, decode_token

    token = create_access_token("user-123", extra_claims={"email": "x@y.com"})
    claims = decode_token(token)
    assert claims["sub"] == "user-123"
    assert claims["email"] == "x@y.com"
    assert claims["type"] == "access"


def test_settings_loads() -> None:
    from app.config import get_settings

    s = get_settings()
    assert s.app_name
    assert s.cors_origins_list


def test_normalizar_estado_pago_inline() -> None:
    from decimal import Decimal

    from app.api.v1.sales import _normalizar_estado_pago

    assert _normalizar_estado_pago(Decimal("0"), Decimal("100")) == "Pagado"
    assert _normalizar_estado_pago(Decimal("100"), Decimal("100")) == "Pendiente"
    assert _normalizar_estado_pago(Decimal("50"), Decimal("100")) == "Abono parcial"
    assert _normalizar_estado_pago(Decimal("0"), Decimal("0")) == "Pagado"


def test_app_starts() -> None:
    """El app FastAPI se construye sin errores."""
    from app.main import app

    routes = [r.path for r in app.routes]
    assert "/health" in routes
    assert "/v1/auth/login" in routes
    assert "/v1/products" in routes
    assert "/v1/sales/orders" in routes
