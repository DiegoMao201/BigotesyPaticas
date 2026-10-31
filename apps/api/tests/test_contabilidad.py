"""Reglas contables del estado de resultados (app/services/contabilidad.py)."""

from datetime import date

from app.services.contabilidad import armar_estado, clasificar_gasto


def test_clasificar_gasto():
    assert clasificar_gasto("Compra Inventario", "Variable") == "inventario"
    assert clasificar_gasto("Inventario", "Fijo") == "inventario"
    assert clasificar_gasto("Otros", "Costo de Venta") == "inventario"
    assert clasificar_gasto("Otros", "Inversión") == "inversion"
    assert clasificar_gasto("Otros", "Abono a crédito") == "credito"
    assert clasificar_gasto("Arriendo", "Operativo") == "operativo"
    assert clasificar_gasto(None, None) == "operativo"


def _cifras(**extra):
    base = {
        "ventas": {
            "ventas_brutas": 1_000_000,
            "descuentos": 5_000,
            "bonos": 5_000,
            "envios": 21_200,
            "ventas_netas": 995_000,
            "n_ventas": 10,
            "dias_con_venta": 5,
        },
        "items": {
            "costo_ventas": 800_000,
            "unidades": 20,
            "unidades_sin_costo": 2,
            "lineas_bajo_costo": 1,
            "perdida_bajo_costo": 18_500,
        },
        "gastos": [
            {"clase": "operativo", "categoria": "Arriendo", "es_fijo": True, "total": 50_000, "n": 1},
            {"clase": "operativo", "categoria": "Otros", "es_fijo": False, "total": 10_000, "n": 2},
            {"clase": "credito", "categoria": "Otros", "es_fijo": False, "total": 580_000, "n": 1},
            {"clase": "inversion", "categoria": "Otros", "es_fijo": False, "total": 300_000, "n": 1},
            {"clase": "inventario", "categoria": "Compra Inventario", "es_fijo": False, "total": 99, "n": 1},
        ],
        "tarjeta": {"monto": 0, "n": 0},
        "compras_mercancia": 700_000,
        "desde": date(2026, 10, 1),
        "hasta": date(2026, 10, 30),
    }
    return {**base, **extra}


def test_credito_inversion_e_inventario_no_son_gasto():
    e = armar_estado(_cifras())
    assert e["gastos_operativos"] == 60_000
    assert e["gastos_fijos"] == 50_000 and e["gastos_variables"] == 10_000
    assert e["fuera_del_resultado"]["abonos_credito"] == 580_000
    assert e["fuera_del_resultado"]["inversiones"] == 300_000
    assert e["fuera_del_resultado"]["compras_como_gasto"] == 99
    assert e["fuera_del_resultado"]["compras_mercancia"] == 700_000
    assert e["fuera_del_resultado"]["envios_cobrados"] == 21_200


def test_cadena_del_resultado():
    e = armar_estado(_cifras())
    assert e["ventas_netas"] == 995_000
    assert e["utilidad_bruta"] == 195_000
    assert e["margen_bruto_pct"] == 19.6
    assert e["utilidad_operacional"] == 135_000
    assert e["comision_tarjeta"] == 0
    assert e["utilidad_neta"] == 135_000
    assert e["periodo"]["dias"] == 30
    assert e["ticket_promedio"] == 99_500


def test_comision_tarjeta_resta_de_la_neta():
    e = armar_estado(_cifras(tarjeta={"monto": 100_000, "n": 2}))
    # 3,4 % + $300 por transacción (config por defecto)
    assert e["comision_tarjeta"] == 4_000
    assert e["utilidad_neta"] == 131_000


def test_punto_de_equilibrio_del_periodo():
    e = armar_estado(_cifras())
    # gastos 60.000 / margen 19,6 % = 306.122
    assert e["punto_equilibrio"] == 306_122
    assert e["cobertura_pct"] == 325.0


def test_calidad_del_dato():
    e = armar_estado(_cifras())
    assert e["calidad"]["unidades_sin_costo"] == 2
    assert e["calidad"]["lineas_bajo_costo"] == 1
    assert e["calidad"]["gastos_sin_clasificar"] == 10_000
