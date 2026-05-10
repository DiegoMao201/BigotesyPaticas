"""
bp_common — biblioteca compartida para BigotesyPaticas.

Este paquete es **opt-in**. La app Streamlit actual sigue funcionando con sus
copias inline de utilitarios. Cuando un módulo se quiera modernizar, sólo
tiene que importar desde aquí:

    from bp_common.currency import clean_currency
    from bp_common.ids import normalizar_id_producto
    from bp_common.pricing import precio_con_margen
    from bp_common.tz import now_co, TZ_CO
    from bp_common.payments import normalizar_estado_pago

Las funciones aquí son **bit-exact** respecto a las versiones originales en
`BigotesyPaticas.py` y `pages/*.py`, validadas por la suite de golden tests
en `tests/golden/`.
"""

__version__ = "0.1.0"
