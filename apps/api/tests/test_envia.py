"""Pruebas puras del servicio de Envia: peso, empaque, destino y precio.

No tocan la red ni la base. Lo que sí pega a Envia se probó a mano contra el
sandbox el 16-oct-2026 (ver la cabecera de app/services/envia.py).
"""

import pytest

from app.services import envia


@pytest.mark.parametrize(
    ("nombre", "esperado"),
    [
        ("Agility Gold Grandes Adultos Azul 15k", 15.0),
        ("Hills Gato Kitten 3,5 Lb (1,59 Kg)", 1.59),
        ("Churu Dog Pollo 4x14g Us611*Verde-Naranja", 0.056),
        ("Organew 100 G", 0.1),
        ("Natural Freshly Spray 240 Ml", 0.24),
        ("Max Perro Cachorro Performance Pollo 2 Kg", 2.0),
        ("Monello Gatitos Pollo1k", 1.0),
        ("Pala Plastica Grande", envia.PESO_POR_DEFECTO_KG),
    ],
)
def test_peso_desde_el_nombre(nombre: str, esperado: float) -> None:
    assert envia.peso_kg_de(nombre) == pytest.approx(esperado, abs=0.001)


def test_peso_del_atributo_manda() -> None:
    assert envia.peso_kg_de("Agility Gold 15k", {"peso_kg": "3"}) == 3.0


def test_empacar_lo_suelto_va_en_una_caja_con_relleno() -> None:
    cajas = envia.empacar([{"nombre": "Organew 100 G", "cantidad": 2}], 40000)
    assert len(cajas) == 1
    # 200 g + 300 g de caja y relleno (el 10 % sería menos)
    assert cajas[0]["weight"] == pytest.approx(0.5)
    assert cajas[0]["declaredValue"] == 40000
    assert cajas[0]["weightUnit"] == "KG" and cajas[0]["lengthUnit"] == "CM"


def test_empacar_cada_saco_es_su_propio_paquete() -> None:
    cajas = envia.empacar([{"nombre": "Agility Gold 15k", "cantidad": 2}], 300000)
    assert len(cajas) == 2
    assert all(c["weight"] == pytest.approx(15.3) for c in cajas)
    assert sum(c["declaredValue"] for c in cajas) == 300000
    # medidas de saco, no de caja
    assert cajas[0]["dimensions"]["length"] >= 60


def test_empacar_saco_mas_sueltos_son_dos_paquetes() -> None:
    cajas = envia.empacar(
        [{"nombre": "Chunky Perro Adulto Pollo 9k", "cantidad": 1},
         {"nombre": "Churu Cat 4x14g", "cantidad": 3, "atributos": {"peso_kg": 0.1}}],
        120000,
    )
    assert len(cajas) == 2
    assert cajas[0]["weight"] == pytest.approx(9.3)
    assert cajas[1]["weight"] == pytest.approx(0.6)
    assert sum(c["declaredValue"] for c in cajas) == 120000


def test_peso_ignora_el_rango_del_animal_y_entiende_onzas() -> None:
    assert envia.peso_kg_de("Nexgard Perros 25 - 50 Kg") == envia.PESO_POR_DEFECTO_KG
    assert envia.peso_kg_de("Bravecto 1M 10-20 Kg") == envia.PESO_POR_DEFECTO_KG
    assert envia.peso_kg_de("Hills Perro Lata K/D 13 Oz") == pytest.approx(0.369, abs=0.001)
    assert envia.peso_kg_de("Br For Cat Castrado Pollo X 10 Kl") == 10.0
    assert envia.peso_kg_de("Royal Canin Gato Urinary Care 400 Grs") == 0.4


def test_destino_separa_calle_y_numero() -> None:
    d = envia.destino_a_envia({
        "nombre": "Cliente", "telefono": "300 123 4567", "calle": "Calle 100 # 15-20",
        "barrio": "Chicó", "ciudad": "Bogotá", "dane": "11001000", "departamento": "dc",
        "postal": "110111", "cedula": "1.020.304.050",
    })
    assert d["street"] == "Calle 100"
    assert d["number"] == "15-20"
    assert d["city"] == "11001000"
    assert d["state"] == "DC"
    assert d["phone"] == "3001234567"
    assert d["identificationNumber"] == "1020304050"
    assert d["country"] == "CO"


def test_destino_sin_numeral_va_entero_en_street() -> None:
    d = envia.destino_a_envia({"calle": "Carrera 7 con 72", "dane": "11001000", "departamento": "DC"})
    assert d["street"] == "Carrera 7 con 72"
    assert d["number"] == ""


def test_precio_al_cliente_redondea_a_la_centena_hacia_arriba() -> None:
    assert envia._precio_cliente(6080.0) == 6100
    assert envia._precio_cliente(19070.0) == 19100
    assert envia._precio_cliente(20000.0) == 20000


def test_departamentos_tienen_codigo_de_dos_letras() -> None:
    assert all(len(c) == 2 for c, _ in envia.DEPARTAMENTOS)
    assert envia.DEPARTAMENTO_NOMBRE["RI"] == "Risaralda"
    assert envia.DEPARTAMENTO_NOMBRE["DC"].startswith("Bogotá")
