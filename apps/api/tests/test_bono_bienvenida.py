"""Reglas del bono de bienvenida PRIMERAPATA (las que promete el correo)."""

from datetime import UTC, datetime, timedelta

from app.services.bono_bienvenida import CODIGO, MINIMO, VALOR, estado, vence_en

ENVIADO = datetime(2026, 10, 29, 20, 39, tzinfo=UTC)


def _fila(**extra):
    base = {"subscribed_at": ENVIADO, "coupon_sent_at": ENVIADO, "coupon_redeemed_at": None}
    return {**base, **extra}


def test_valores_prometidos_en_el_correo():
    assert CODIGO == "PRIMERAPATA"
    assert VALOR == 5000
    assert MINIMO == 30000


def test_pendiente_dentro_de_los_30_dias():
    assert estado(_fila(), ENVIADO + timedelta(days=29, hours=23)) == "pendiente"


def test_vence_a_los_30_dias():
    assert vence_en(_fila()) == ENVIADO + timedelta(days=30)
    assert estado(_fila(), ENVIADO + timedelta(days=30, minutes=1)) == "vencido"


def test_canjeado_manda_sobre_vencido():
    fila = _fila(coupon_redeemed_at=ENVIADO + timedelta(days=2))
    assert estado(fila, ENVIADO + timedelta(days=90)) == "canjeado"


def test_sin_fecha_de_envio_cuenta_desde_la_suscripcion():
    fila = _fila(coupon_sent_at=None)
    assert vence_en(fila) == ENVIADO + timedelta(days=30)
