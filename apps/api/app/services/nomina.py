"""Liquidación de nómina quincenal (15-oct-2026).

Toda la aritmética legal vive aquí, en funciones puras sin base de datos, para
poderla comprobar con números a mano. Lo que entra: el salario mensual, el
auxilio mensual, los porcentajes de deducción y los días trabajados. Lo que sale:
el desprendible completo y la provisión de prestaciones de esa quincena.

LA CUENTA, Y POR QUÉ ES ASÍ (Código Sustantivo del Trabajo, régimen ordinario):

- El mes laboral es de **30 días** y cada quincena de **15**, sin importar que el
  mes tenga 28 o 31. Así liquida todo el país y así cuadra el mes entero con el
  salario mensual completo.
- **Devengado** = salario × días/30 + auxilio de transporte × días/30. El auxilio
  se paga a quien gana hasta 2 SMMLV.
- **Deducciones del trabajador**: salud 4 % y pensión 4 % sobre el SALARIO; el
  auxilio de transporte no es base de cotización. Como el salario es menor a
  4 SMMLV, no aplica fondo de solidaridad pensional.
- **Provisión de prestaciones** (lo que el empleador va debiendo aunque no lo
  consigne esta quincena): cesantías 1/12 y prima 1/12 sobre salario + auxilio;
  intereses a las cesantías 12 % anual sobre las cesantías (= 1 % de la base);
  vacaciones 15 días por año sobre el salario solo (= salario/24).
- Todo se redondea **al peso** (medio peso va al par, como en contabilidad), que es
  como se consigna: así 875.452,5 + 124.547,5 suman exactamente 1.000.000.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal

PESO = Decimal("1")
DIAS_MES = 30
DIAS_QUINCENA = 15


def _peso(v: Decimal) -> Decimal:
    return v.quantize(PESO, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class Periodo:
    inicio: date
    fin: date
    quincena: int  # 1 = del 1 al 15, 2 = del 16 al último día

    @property
    def etiqueta(self) -> str:
        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        ]  # fmt: skip
        return f"{self.inicio.day} al {self.fin.day} de {meses[self.inicio.month - 1]} de {self.inicio.year}"

    @property
    def clave(self) -> str:
        return f"{self.inicio:%Y-%m}-Q{self.quincena}"


def periodo_que_contiene(d: date) -> Periodo:
    """La quincena a la que pertenece una fecha."""
    if d.day <= 15:
        return Periodo(date(d.year, d.month, 1), date(d.year, d.month, 15), 1)
    ultimo = calendar.monthrange(d.year, d.month)[1]
    return Periodo(date(d.year, d.month, 16), date(d.year, d.month, ultimo), 2)


def periodo_siguiente(p: Periodo) -> Periodo:
    if p.quincena == 1:
        return periodo_que_contiene(date(p.inicio.year, p.inicio.month, 16))
    y, m = (p.inicio.year + 1, 1) if p.inicio.month == 12 else (p.inicio.year, p.inicio.month + 1)
    return periodo_que_contiene(date(y, m, 1))


def dias_laborales(p: Periodo, fecha_ingreso: date, fecha_retiro: date | None = None) -> int:
    """Días de la quincena que cubre el contrato, en la convención de 30 días.

    Entró el 1: 15 días. Entró el 10 de la primera quincena: 6 días (del 10 al 15).
    Entró el 20 de la segunda: 11 días (del 20 al "30", así el mes tenga 31).
    """
    if fecha_ingreso > p.fin:
        return 0
    if fecha_retiro is not None and fecha_retiro < p.inicio:
        return 0
    inicio_dia = p.inicio.day
    fin_dia = DIAS_QUINCENA if p.quincena == 1 else DIAS_MES
    desde = max(inicio_dia, fecha_ingreso.day) if fecha_ingreso >= p.inicio else inicio_dia
    hasta = fin_dia
    if fecha_retiro is not None and fecha_retiro <= p.fin:
        hasta = min(fin_dia, fecha_retiro.day)
    return max(0, min(DIAS_QUINCENA, hasta - desde + 1))


@dataclass
class Liquidacion:
    dias_trabajados: int
    salario_base: Decimal
    aux_base: Decimal
    pct_salud: Decimal
    pct_pension: Decimal
    dev_salario: Decimal = Decimal(0)
    dev_auxilio: Decimal = Decimal(0)
    otros_devengados: Decimal = Decimal(0)
    total_devengado: Decimal = Decimal(0)
    ded_salud: Decimal = Decimal(0)
    ded_pension: Decimal = Decimal(0)
    otros_descuentos: Decimal = Decimal(0)
    total_deducciones: Decimal = Decimal(0)
    neto: Decimal = Decimal(0)
    prov_cesantias: Decimal = Decimal(0)
    prov_intereses: Decimal = Decimal(0)
    prov_prima: Decimal = Decimal(0)
    prov_vacaciones: Decimal = Decimal(0)
    total_provision: Decimal = Decimal(0)
    notas: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "dias_trabajados": self.dias_trabajados,
            "salario_base": float(self.salario_base),
            "aux_base": float(self.aux_base),
            "pct_salud": float(self.pct_salud),
            "pct_pension": float(self.pct_pension),
            "dev_salario": float(self.dev_salario),
            "dev_auxilio": float(self.dev_auxilio),
            "otros_devengados": float(self.otros_devengados),
            "total_devengado": float(self.total_devengado),
            "ded_salud": float(self.ded_salud),
            "ded_pension": float(self.ded_pension),
            "otros_descuentos": float(self.otros_descuentos),
            "total_deducciones": float(self.total_deducciones),
            "neto": float(self.neto),
            "prov_cesantias": float(self.prov_cesantias),
            "prov_intereses": float(self.prov_intereses),
            "prov_prima": float(self.prov_prima),
            "prov_vacaciones": float(self.prov_vacaciones),
            "total_provision": float(self.total_provision),
            "notas": self.notas,
        }


def liquidar(
    *,
    salario_mensual: Decimal,
    aux_mensual: Decimal,
    pct_salud: Decimal,
    pct_pension: Decimal,
    dias: int,
    smmlv: Decimal,
    otros_devengados: Decimal = Decimal(0),
    otros_descuentos: Decimal = Decimal(0),
) -> Liquidacion:
    """Liquida una quincena. `dias` entre 0 y 15."""
    dias = max(0, min(DIAS_QUINCENA, int(dias)))
    liq = Liquidacion(
        dias_trabajados=dias,
        salario_base=salario_mensual,
        aux_base=aux_mensual,
        pct_salud=pct_salud,
        pct_pension=pct_pension,
    )
    factor = Decimal(dias) / Decimal(DIAS_MES)

    liq.dev_salario = _peso(salario_mensual * factor)
    # El auxilio de transporte solo aplica hasta 2 salarios mínimos.
    if salario_mensual <= smmlv * 2:
        liq.dev_auxilio = _peso(aux_mensual * factor)
    else:
        liq.dev_auxilio = Decimal(0)
        liq.notas.append("Sin auxilio de transporte: salario superior a 2 SMMLV.")
    liq.otros_devengados = _peso(Decimal(otros_devengados or 0))
    liq.total_devengado = liq.dev_salario + liq.dev_auxilio + liq.otros_devengados

    # Salud y pensión se calculan sobre el salario devengado, nunca sobre el auxilio.
    liq.ded_salud = _peso(liq.dev_salario * pct_salud / Decimal(100))
    liq.ded_pension = _peso(liq.dev_salario * pct_pension / Decimal(100))
    liq.otros_descuentos = _peso(Decimal(otros_descuentos or 0))
    liq.total_deducciones = liq.ded_salud + liq.ded_pension + liq.otros_descuentos
    liq.neto = liq.total_devengado - liq.total_deducciones

    # Provisión de prestaciones sociales de esta quincena.
    base_prest = liq.dev_salario + liq.dev_auxilio
    liq.prov_cesantias = _peso(base_prest / Decimal(12))
    liq.prov_intereses = _peso(liq.prov_cesantias * Decimal("0.12"))
    liq.prov_prima = _peso(base_prest / Decimal(12))
    liq.prov_vacaciones = _peso(liq.dev_salario / Decimal(24))
    liq.total_provision = (
        liq.prov_cesantias + liq.prov_intereses + liq.prov_prima + liq.prov_vacaciones
    )
    if liq.neto < 0:
        liq.notas.append("Los descuentos superan lo devengado: revisa los otros descuentos.")
    return liq


def provision_mensual(salario_mensual: Decimal, aux_mensual: Decimal) -> dict[str, float]:
    """Cuánto hay que ir apartando cada mes por prestaciones (mes completo)."""
    base = salario_mensual + aux_mensual
    ces = _peso(base / Decimal(12))
    inte = _peso(ces * Decimal("0.12"))
    prima = _peso(base / Decimal(12))
    vac = _peso(salario_mensual / Decimal(24))
    return {
        "cesantias": float(ces),
        "intereses_cesantias": float(inte),
        "prima": float(prima),
        "vacaciones": float(vac),
        "total": float(ces + inte + prima + vac),
    }
