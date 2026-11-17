"""Desprendible de nómina y contrato de trabajo en PDF (WeasyPrint, 15-oct-2026).

Mismo motor y misma identidad que el comprobante de venta (`invoice_pdf`): el
logo va embebido en base64 y el PDF se arma desde las cifras congeladas del pago,
así que un desprendible de hace un año se vuelve a generar idéntico.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.services.invoice_pdf import LOGO_PNG_B64, generate_invoice_pdf

# Datos del empleador. Son los mismos que publica la web (business-info.ts) y la
# política de privacidad del store: persona natural, régimen ordinario, no responsable de IVA (RUT).
EMPRESA = {
    "nombre": "Bigotes y Paticas",
    "razon_social": "Diego Mauricio García — Bigotes y Paticas",
    "representante": "Diego Mauricio García",
    "nit": "1088266407-7",
    "cedula_representante": "1088266407",
    "direccion": "Samara Plaza Mall, Cl. 15 #3A-07 Local 2, Dosquebradas, Risaralda",
    "ciudad": "Dosquebradas, Risaralda",
    "telefono": "320 687 6633",
    "email": "bigotesypaticasdosquebradas@gmail.com",
}

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]  # fmt: skip


def _money(v: Decimal | float | int) -> str:
    n = int(Decimal(str(v)).quantize(Decimal("1")))
    return "$ " + f"{n:,}".replace(",", ".")


def _fecha_larga(d: date) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _fecha_corta(d: date) -> str:
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


_BASE_CSS = """
@page { size: letter; margin: 16mm 16mm 18mm 16mm; }
* { box-sizing: border-box; }
body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #1c1917; font-size: 10pt; margin: 0; }
.brand-bar { height: 5px; background: linear-gradient(90deg, #0d4a45, #14b8a6, #f59e0b); margin: -16mm -16mm 10mm -16mm; }
.header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8mm; }
.brand { display: flex; gap: 10px; align-items: center; }
.brand img { width: 52px; height: 52px; border-radius: 12px; }
.brand-name { font-weight: 800; font-size: 15pt; color: #0d4a45; }
.brand-sub { font-size: 8.5pt; color: #57534e; }
.doc-meta { text-align: right; }
.doc-eyebrow { font-size: 8pt; letter-spacing: .14em; text-transform: uppercase; color: #78716c; }
.doc-title { font-size: 15pt; font-weight: 800; color: #0d4a45; }
.doc-sub { font-size: 9pt; color: #57534e; }
.grid { display: flex; gap: 8px; margin-bottom: 7mm; }
.card { flex: 1; border: 1px solid #e7e5e4; border-radius: 10px; padding: 9px 11px; background: #fafaf9; }
.card .label { font-size: 7.5pt; text-transform: uppercase; letter-spacing: .1em; color: #78716c; margin-bottom: 3px; }
.card .value { font-weight: 700; font-size: 10.5pt; }
.card .sub { font-size: 8.5pt; color: #57534e; }
table { width: 100%; border-collapse: collapse; margin-bottom: 5mm; }
th { text-align: left; font-size: 7.5pt; text-transform: uppercase; letter-spacing: .1em; color: #78716c; padding: 6px 8px; border-bottom: 1.5px solid #d6d3d1; }
td { padding: 6px 8px; border-bottom: 1px solid #efedeb; font-size: 9.5pt; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
tr.total td { font-weight: 800; border-top: 1.5px solid #0d4a45; border-bottom: none; background: #f0fdfa; }
.neto { border: 2px solid #0d4a45; border-radius: 12px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; background: #f0fdfa; margin: 4mm 0 6mm; }
.neto .l { font-size: 9pt; text-transform: uppercase; letter-spacing: .12em; color: #0d4a45; font-weight: 700; }
.neto .v { font-size: 18pt; font-weight: 900; color: #0d4a45; }
.note { font-size: 8.5pt; color: #57534e; line-height: 1.45; }
.footer { margin-top: 8mm; padding-top: 4mm; border-top: 1px solid #e7e5e4; font-size: 8pt; color: #78716c; }
.firmas { display: flex; gap: 20mm; margin-top: 16mm; }
.firma { flex: 1; border-top: 1px solid #1c1917; padding-top: 4px; font-size: 8.5pt; }
h2 { font-size: 10.5pt; color: #0d4a45; margin: 6mm 0 2mm; text-transform: uppercase; letter-spacing: .08em; }
p { margin: 0 0 3mm; line-height: 1.5; text-align: justify; }
"""


def _header(eyebrow: str, titulo: str, sub: str) -> str:
    return f"""
    <div class="brand-bar"></div>
    <div class="header">
      <div class="brand">
        <img src="data:image/png;base64,{LOGO_PNG_B64}" alt="Bigotes y Paticas" />
        <div>
          <div class="brand-name">{EMPRESA["nombre"]}</div>
          <div class="brand-sub">{EMPRESA["razon_social"]} · NIT {EMPRESA["nit"]}</div>
          <div class="brand-sub">{EMPRESA["direccion"]}</div>
        </div>
      </div>
      <div class="doc-meta">
        <div class="doc-eyebrow">{eyebrow}</div>
        <div class="doc-title">{titulo}</div>
        <div class="doc-sub">{sub}</div>
      </div>
    </div>"""


def render_desprendible_html(*, payroll, employee, periodo_etiqueta: str) -> str:
    """Desprendible de pago de una quincena ya liquidada (cifras del registro)."""
    otros_dev = ""
    if Decimal(payroll.otros_devengados or 0) > 0:
        otros_dev = f"<tr><td>Otros devengados</td><td class='num'>{_money(payroll.otros_devengados)}</td></tr>"
    otros_ded = ""
    if Decimal(payroll.otros_descuentos or 0) > 0:
        desc = payroll.descripcion_otros or "Otros descuentos"
        otros_ded = f"<tr><td>{desc}</td><td class='num'>{_money(payroll.otros_descuentos)}</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><style>{_BASE_CSS}</style></head>
<body>
  {_header("Desprendible de nómina", f"N.º {payroll.consecutivo:05d}", f"Pagado el {_fecha_larga(payroll.fecha_pago)}")}

  <div class="grid">
    <div class="card">
      <div class="label">Trabajador</div>
      <div class="value">{employee.nombre}</div>
      <div class="sub">C.C. {employee.documento} · {employee.cargo}</div>
      <div class="sub">Ingreso: {_fecha_corta(employee.fecha_ingreso)}</div>
    </div>
    <div class="card">
      <div class="label">Período liquidado</div>
      <div class="value">{periodo_etiqueta}</div>
      <div class="sub">{payroll.dias_trabajados} días · quincena {payroll.quincena}</div>
      <div class="sub">Pago por {payroll.metodo_pago}</div>
    </div>
    <div class="card">
      <div class="label">Bases mensuales</div>
      <div class="value">{_money(payroll.salario_base)}</div>
      <div class="sub">Salario básico</div>
      <div class="sub">Aux. transporte {_money(payroll.aux_base)}</div>
    </div>
  </div>

  <table>
    <thead><tr><th>Devengado</th><th class="num">Valor</th></tr></thead>
    <tbody>
      <tr><td>Salario básico ({payroll.dias_trabajados} días)</td><td class="num">{_money(payroll.dev_salario)}</td></tr>
      <tr><td>Auxilio de transporte</td><td class="num">{_money(payroll.dev_auxilio)}</td></tr>
      {otros_dev}
      <tr class="total"><td>Total devengado</td><td class="num">{_money(payroll.total_devengado)}</td></tr>
    </tbody>
  </table>

  <table>
    <thead><tr><th>Deducciones</th><th class="num">Valor</th></tr></thead>
    <tbody>
      <tr><td>Aporte salud ({payroll.pct_salud:g} % sobre el salario)</td><td class="num">{_money(payroll.ded_salud)}</td></tr>
      <tr><td>Aporte pensión ({payroll.pct_pension:g} % sobre el salario)</td><td class="num">{_money(payroll.ded_pension)}</td></tr>
      {otros_ded}
      <tr class="total"><td>Total deducciones</td><td class="num">{_money(payroll.total_deducciones)}</td></tr>
    </tbody>
  </table>

  <div class="neto"><span class="l">Neto pagado</span><span class="v">{_money(payroll.neto)}</span></div>

  <p class="note">Los aportes a seguridad social a cargo del empleador (salud, pensión, riesgos
  laborales y caja de compensación) y las prestaciones sociales (prima, cesantías, intereses
  y vacaciones) se liquidan y pagan por separado en las fechas de ley; no hacen parte de este
  desprendible. El auxilio de transporte no es base de cotización.</p>

  <div class="footer">
    {EMPRESA["razon_social"]} · NIT {EMPRESA["nit"]} · {EMPRESA["direccion"]} · {EMPRESA["telefono"]} · {EMPRESA["email"]}<br/>
    Documento generado por el sistema de nómina de Bigotes y Paticas. Conserva este desprendible como soporte de pago.
  </div>
</body></html>"""


def render_contrato_html(*, employee, smmlv: Decimal, aux: Decimal) -> str:
    """Contrato individual de trabajo a término indefinido, salario mínimo legal."""
    tipo = "a término indefinido" if employee.tipo_contrato == "indefinido" else employee.tipo_contrato
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><style>{_BASE_CSS}
    .partes td {{ border: none; padding: 2px 8px 2px 0; font-size: 9.5pt; }}
    .partes td.k {{ color: #78716c; width: 34%; }}
  </style></head>
<body>
  {_header("Contrato individual de trabajo", tipo.capitalize(), f"Inicio: {_fecha_larga(employee.fecha_ingreso)}")}

  <div class="grid">
    <div class="card">
      <div class="label">Empleador</div>
      <div class="value">{EMPRESA["representante"]}</div>
      <div class="sub">C.C. {EMPRESA["cedula_representante"]} · NIT {EMPRESA["nit"]}</div>
      <div class="sub">Establecimiento: {EMPRESA["nombre"]}</div>
      <div class="sub">{EMPRESA["direccion"]}</div>
    </div>
    <div class="card">
      <div class="label">Trabajador</div>
      <div class="value">{employee.nombre}</div>
      <div class="sub">C.C. {employee.documento}</div>
      <div class="sub">{employee.email or ""}</div>
    </div>
  </div>

  <table class="partes">
    <tr><td class="k">Cargo</td><td><strong>{employee.cargo}</strong></td></tr>
    <tr><td class="k">Clase de contrato</td><td>Contrato individual de trabajo {tipo}</td></tr>
    <tr><td class="k">Fecha de inicio</td><td>{_fecha_larga(employee.fecha_ingreso)}</td></tr>
    <tr><td class="k">Lugar de trabajo</td><td>{EMPRESA["direccion"]}, y las rutas de domicilio que asigne el empleador en Dosquebradas y Pereira</td></tr>
    <tr><td class="k">Salario</td><td><strong>{_money(smmlv)}</strong> mensuales (salario mínimo legal mensual vigente)</td></tr>
    <tr><td class="k">Auxilio de transporte</td><td>{_money(aux)} mensuales (auxilio legal vigente)</td></tr>
    <tr><td class="k">Forma de pago</td><td>Por quincenas vencidas, los días 15 y último de cada mes, con desprendible de pago</td></tr>
    <tr><td class="k">Período de prueba</td><td>Dos (2) meses contados desde la fecha de inicio</td></tr>
  </table>

  <h2>Cláusulas</h2>
  <p><strong>Primera. Objeto.</strong> El trabajador se obliga a prestar personalmente sus servicios al
  empleador en el cargo de <strong>{employee.cargo}</strong>, realizando la entrega de pedidos a
  domicilio, el apoyo en la tienda y las demás labores conexas o complementarias que correspondan
  a la naturaleza del cargo, bajo la subordinación del empleador y conforme a sus instrucciones.</p>

  <p><strong>Segunda. Duración.</strong> El contrato es {tipo}, con fecha de inicio el
  {_fecha_larga(employee.fecha_ingreso)}, y se rige por el Código Sustantivo del Trabajo y las normas
  que lo adicionen o modifiquen. Los dos (2) primeros meses se consideran período de prueba, durante
  el cual cualquiera de las partes puede darlo por terminado sin previo aviso ni indemnización.</p>

  <p><strong>Tercera. Salario y auxilio.</strong> El empleador pagará al trabajador el salario mínimo
  legal mensual vigente, actualmente {_money(smmlv)}, más el auxilio de transporte legal, actualmente
  {_money(aux)}. Ambos valores se ajustarán automáticamente cada vez que el Gobierno Nacional los
  modifique. El pago se hará por quincenas vencidas y de cada pago se entregará al trabajador un
  desprendible con el detalle de lo devengado y de las deducciones de ley.</p>

  <p><strong>Cuarta. Jornada.</strong> La jornada de trabajo será la máxima legal vigente, distribuida
  de lunes a sábado según el horario de atención del establecimiento, con los descansos de ley. El
  trabajo en horas extra, dominical o festivo se reconocerá conforme a la ley, previa autorización del
  empleador.</p>

  <p><strong>Quinta. Seguridad social y prestaciones.</strong> El empleador afiliará al trabajador al
  Sistema de Seguridad Social Integral (salud, pensión y riesgos laborales) y a una caja de
  compensación familiar, y asumirá los aportes a su cargo. Del salario del trabajador se descontarán
  únicamente los aportes que la ley le asigna (salud y pensión) y los demás descuentos que él autorice
  por escrito. El trabajador tendrá derecho a prima de servicios, cesantías e intereses a las
  cesantías, vacaciones y las demás prestaciones de ley.</p>

  <p><strong>Sexta. Obligaciones del trabajador.</strong> Cumplir las instrucciones del empleador;
  tratar con respeto a los clientes y cuidar los productos, el dinero y los elementos que se le
  confíen para las entregas; rendir cuentas de los cobros recibidos en cada domicilio el mismo día;
  observar las normas de tránsito y de seguridad; y guardar reserva sobre la información de clientes
  y del negocio.</p>

  <p><strong>Séptima. Obligaciones del empleador.</strong> Pagar el salario y el auxilio en las fechas
  pactadas, afiliar y cotizar a la seguridad social, suministrar los elementos necesarios para la
  labor y cumplir las demás obligaciones que le impone la ley.</p>

  <p><strong>Octava. Terminación.</strong> El contrato podrá terminar por las causales previstas en el
  Código Sustantivo del Trabajo. A su terminación, el empleador liquidará y pagará al trabajador las
  prestaciones sociales y demás acreencias laborales a que tenga derecho.</p>

  <p><strong>Novena. Domicilio.</strong> Para todos los efectos, las partes fijan como domicilio
  contractual el municipio de {EMPRESA["ciudad"]}.</p>

  <p>Para constancia se firma en {EMPRESA["ciudad"]}, el {_fecha_larga(employee.fecha_ingreso)}.</p>

  <div class="firmas">
    <div class="firma"><strong>{EMPRESA["representante"]}</strong><br/>C.C. {EMPRESA["cedula_representante"]}<br/>Empleador</div>
    <div class="firma"><strong>{employee.nombre}</strong><br/>C.C. {employee.documento}<br/>Trabajador</div>
  </div>

  <div class="footer">
    {EMPRESA["razon_social"]} · NIT {EMPRESA["nit"]} · {EMPRESA["direccion"]} · {EMPRESA["telefono"]} · {EMPRESA["email"]}
  </div>
</body></html>"""


def html_a_pdf(html: str) -> bytes:
    return generate_invoice_pdf(html)


# ────────────────── Liquidación final (17-nov-2026) ──────────────────────

MOTIVOS = {
    "mutuo_acuerdo": "mutuo acuerdo entre las partes (artículo 61, literal b, del Código Sustantivo del Trabajo)",
    "renuncia": "renuncia voluntaria del trabajador (artículo 61, literal h, del Código Sustantivo del Trabajo)",
}


def render_liquidacion_html(
    *,
    employee,
    liq: dict,
    fecha_retiro: date,
    fecha_documento: date,
    motivo: str,
    razon: str,
    pagos: list,
    consecutivo: int,
) -> str:
    """Carta, liquidación definitiva, acta de terminación con paz y salvo, y
    certificado laboral: los cuatro documentos de un cierre de contrato."""
    nombre = employee.nombre
    primer = nombre.split(" ")[0]
    causal = MOTIVOS.get(motivo, motivo)
    # Período de prueba pactado en el contrato: 2 meses desde el ingreso.
    ing = employee.fecha_ingreso
    m = ing.month + 2
    fin_prueba = date(ing.year + (m - 1) // 12, (m - 1) % 12 + 1, ing.day) - timedelta(days=1)
    en_prueba = fecha_retiro <= fin_prueba

    filas_pagos = "".join(
        f"<tr><td>N.º {p.consecutivo:05d}</td><td>{_fecha_corta(p.periodo_inicio)} al {_fecha_corta(p.periodo_fin)}</td>"
        f"<td class='num'>{p.dias_trabajados}</td><td>{_fecha_corta(p.fecha_pago)}</td><td class='num'>{_money(p.neto)}</td></tr>"
        for p in pagos
    )
    ultimo_pago = pagos[-1] if pagos else None
    total = liq["total"]
    nota_prueba = (
        f" La terminación ocurre dentro del período de prueba pactado (hasta el {_fecha_larga(fin_prueba)}),"
        " por lo que, además, no hay lugar a preaviso ni a indemnización alguna."
        if en_prueba
        else ""
    )
    footer = f"""<div class="footer">{EMPRESA["razon_social"]} · NIT {EMPRESA["nit"]} · {EMPRESA["direccion"]} · {EMPRESA["telefono"]} · {EMPRESA["email"]}</div>"""
    firmas = f"""
  <div class="firmas">
    <div class="firma"><strong>{EMPRESA["representante"]}</strong><br/>C.C. {EMPRESA["cedula_representante"]}<br/>Empleador</div>
    <div class="firma"><strong>{nombre}</strong><br/>C.C. {employee.documento}<br/>Trabajador</div>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><style>{_BASE_CSS}
  .salto {{ page-break-before: always; }}
  .header {{ margin-bottom: 5mm; }}
  p {{ font-size: 9.8pt; line-height: 1.42; margin: 0 0 2.4mm; }}
  .destino {{ margin: 0 0 4mm; line-height: 1.4; }}
  .asunto {{ font-weight: 700; margin: 0 0 4mm; }}
  .firmas {{ margin-top: 12mm; }}
  .footer {{ margin-top: 5mm; }}
  table {{ margin-bottom: 3mm; }}
  td {{ padding: 5px 8px; }}
  .neto {{ margin: 2mm 0 4mm; }}
  .formula {{ color: #78716c; font-size: 8.5pt; }}
  .firma-sola {{ width: 70mm; margin-top: 13mm; border-top: 1px solid #1c1917; padding-top: 4px; font-size: 8.5pt; }}
</style></head>
<body>

<div class="carta">
  {_header("Comunicación", "Terminación del contrato", f"{EMPRESA['ciudad']}, {_fecha_larga(fecha_documento)}")}
  <div class="destino">Señor<br/><strong>{nombre}</strong><br/>C.C. {employee.documento}<br/>{employee.email or ""}</div>
  <p class="asunto">Asunto: terminación del contrato de trabajo y liquidación definitiva de prestaciones sociales.</p>
  <p>Apreciado {primer}:</p>
  <p>Por medio de la presente le confirmamos que el contrato individual de trabajo {("a término indefinido" if employee.tipo_contrato == "indefinido" else employee.tipo_contrato)}
  que usted celebró con {EMPRESA["representante"]}, propietario del establecimiento {EMPRESA["nombre"]}, en el cargo de
  <strong>{employee.cargo}</strong>, vigente desde el {_fecha_larga(employee.fecha_ingreso)}, terminó el
  <strong>{_fecha_larga(fecha_retiro)}</strong>, último día laborado, por {causal}{(", " + razon) if razon else ""}.{nota_prueba}</p>
  <p>Su salario y su auxilio de transporte quedaron pagados hasta el {_fecha_larga(fecha_retiro)}{f" con el desprendible N.º {ultimo_pago.consecutivo:05d}" if ultimo_pago else ""}.
  Adjunto encontrará la liquidación definitiva de sus prestaciones sociales por los {liq["dias_laborados"]} días laborados,
  por un valor total de <strong>{_money(total)}</strong>, que se le consignará a la cuenta en la que recibe su salario.
  Ese valor corresponde a cesantías, intereses a las cesantías, prima de servicios y vacaciones causadas y no disfrutadas;
  no se le hace ningún descuento.</p>
  <p>Le informamos además que:</p>
  <p>1. Su retiro se reportará en la planilla de seguridad social (PILA) del mes de {MESES[fecha_retiro.month - 1]},
  con aportes cubiertos hasta el {_fecha_larga(fecha_retiro)}.<br/>
  2. Tiene derecho a realizarse el examen médico ocupacional de egreso, a cargo del empleador. Si desea hacérselo,
  por favor avísenos dentro de los cinco (5) días siguientes al recibo de esta comunicación para programarlo.<br/>
  3. Adjuntamos su certificado laboral y el acta de terminación con paz y salvo, que le pedimos firmar y devolver.</p>
  <p>Le agradecemos sinceramente el compromiso y el trabajo que dedicó a {EMPRESA["nombre"]} y a nuestros clientes.
  Lamentamos la situación familiar que motiva su retiro y le deseamos que todo se resuelva pronto. Las puertas de la
  tienda quedan abiertas para usted.</p>
  <p>Cordialmente,</p>
  <div class="firma-sola"><strong>{EMPRESA["representante"]}</strong><br/>C.C. {EMPRESA["cedula_representante"]}<br/>Empleador · {EMPRESA["nombre"]}</div>
  {footer}
</div>

<div class="salto">
  {_header("Liquidación definitiva", f"N.º L-{consecutivo:05d}", f"Elaborada el {_fecha_larga(fecha_documento)}")}
  <div class="grid">
    <div class="card"><div class="label">Trabajador</div><div class="value">{nombre}</div>
      <div class="sub">C.C. {employee.documento} · {employee.cargo}</div><div class="sub">Contrato {employee.tipo_contrato}</div></div>
    <div class="card"><div class="label">Tiempo de servicio</div><div class="value">{liq["dias_laborados"]} días</div>
      <div class="sub">Ingreso: {_fecha_corta(employee.fecha_ingreso)}</div><div class="sub">Retiro: {_fecha_corta(fecha_retiro)}</div></div>
    <div class="card"><div class="label">Bases mensuales</div><div class="value">{_money(liq["salario_base"])}</div>
      <div class="sub">Salario básico</div><div class="sub">Aux. transporte {_money(liq["aux_base"])}</div></div>
  </div>
  <table>
    <thead><tr><th>Concepto</th><th>Cálculo</th><th class="num">Valor</th></tr></thead>
    <tbody>
      <tr><td>Cesantías</td><td class="formula">{_money(liq["base_prestaciones"])} × {liq["dias_laborados"]} días / 360</td><td class="num">{_money(liq["cesantias"])}</td></tr>
      <tr><td>Intereses a las cesantías</td><td class="formula">cesantías × {liq["dias_laborados"]} días × 12 % / 360</td><td class="num">{_money(liq["intereses_cesantias"])}</td></tr>
      <tr><td>Prima de servicios ({"1.er" if fecha_retiro.month <= 6 else "2.º"} semestre {fecha_retiro.year})</td><td class="formula">{_money(liq["base_prestaciones"])} × {liq["dias_prima"]} días / 360</td><td class="num">{_money(liq["prima"])}</td></tr>
      <tr><td>Vacaciones no disfrutadas ({str(liq["dias_vacaciones"]).replace(".", ",")} días)</td><td class="formula">{_money(liq["salario_base"])} × {liq["dias_laborados"]} días / 720</td><td class="num">{_money(liq["vacaciones"])}</td></tr>
      <tr><td>Salarios pendientes</td><td class="formula">pagados hasta el {_fecha_corta(fecha_retiro)}</td><td class="num">{_money(0)}</td></tr>
      <tr><td>Indemnización</td><td class="formula">no aplica: {"mutuo acuerdo" if motivo == "mutuo_acuerdo" else "renuncia"}{" en período de prueba" if en_prueba else ""}</td><td class="num">{_money(0)}</td></tr>
      <tr><td>Deducciones</td><td class="formula">las prestaciones no son base de aportes</td><td class="num">{_money(0)}</td></tr>
      <tr class="total"><td colspan="2">Total a pagar</td><td class="num">{_money(total)}</td></tr>
    </tbody>
  </table>
  <div class="neto"><span class="l">Neto a pagar al trabajador</span><span class="v">{_money(total)}</span></div>
  <h2>Salarios pagados durante el contrato</h2>
  <table>
    <thead><tr><th>Desprendible</th><th>Período</th><th class="num">Días</th><th>Pagado</th><th class="num">Neto</th></tr></thead>
    <tbody>{filas_pagos}</tbody>
  </table>
  <p class="note">Bases: salario mínimo legal mensual vigente y auxilio de transporte legal (el trabajador devengaba
  hasta dos salarios mínimos). Cesantías y prima incluyen el auxilio de transporte; las vacaciones se liquidan sobre el
  salario solo. Días en mes comercial de 30 días. Por terminar el contrato antes del 31 de diciembre, las cesantías se
  pagan directamente al trabajador.</p>
  {firmas}
  {footer}
</div>

<div class="salto">
  {_header("Acta de terminación", "Paz y salvo", f"{EMPRESA['ciudad']}, {_fecha_larga(fecha_documento)}")}
  <p>Entre los suscritos, <strong>{EMPRESA["representante"]}</strong>, identificado con C.C. {EMPRESA["cedula_representante"]},
  propietario del establecimiento {EMPRESA["nombre"]} (NIT {EMPRESA["nit"]}), en adelante el EMPLEADOR, y
  <strong>{nombre}</strong>, identificado con C.C. {employee.documento}, en adelante el TRABAJADOR, hacemos constar:</p>
  <p><strong>Primero.</strong> Que entre las partes existió un contrato individual de trabajo {employee.tipo_contrato}
  para el cargo de {employee.cargo}, desde el {_fecha_larga(employee.fecha_ingreso)}.</p>
  <p><strong>Segundo.</strong> Que el contrato terminó el {_fecha_larga(fecha_retiro)} por {causal}{(", " + razon) if razon else ""},
  decisión que el TRABAJADOR declara haber tomado de manera libre y voluntaria, sin presión de ninguna clase.{nota_prueba}</p>
  <p><strong>Tercero.</strong> Que el EMPLEADOR pagó al TRABAJADOR la totalidad de los salarios y auxilios de transporte
  causados hasta el {_fecha_larga(fecha_retiro)}, y le paga en este acto la liquidación definitiva N.º L-{consecutivo:05d}
  por <strong>{_money(total)}</strong>, que comprende cesantías ({_money(liq["cesantias"])}), intereses a las cesantías
  ({_money(liq["intereses_cesantias"])}), prima de servicios ({_money(liq["prima"])}) y vacaciones no disfrutadas
  ({_money(liq["vacaciones"])}).</p>
  <p><strong>Cuarto.</strong> Que con el recibo de dicho valor el TRABAJADOR declara al EMPLEADOR a paz y salvo por todo
  concepto de salarios, prestaciones sociales, vacaciones e indemnizaciones derivados del contrato de trabajo, sin perjuicio
  de los derechos ciertos e indiscutibles que la ley le reconoce. A su vez, el TRABAJADOR declara haber devuelto los
  elementos, dineros y cobros de domicilios que tuvo a su cargo, y el EMPLEADOR lo declara a paz y salvo por ese concepto.</p>
  <p><strong>Quinto.</strong> Que el TRABAJADOR fue informado de su derecho a realizarse el examen médico ocupacional de egreso.</p>
  <p>Para constancia se firma en {EMPRESA["ciudad"]}, el ____ de {MESES[fecha_documento.month - 1]} de {fecha_documento.year}.</p>
  {firmas}
  {footer}
</div>

<div class="salto carta">
  {_header("Certificado laboral", "Constancia", f"{EMPRESA['ciudad']}, {_fecha_larga(fecha_documento)}")}
  <p style="text-align:center;font-weight:700;margin:8mm 0 5mm">EL SUSCRITO EMPLEADOR CERTIFICA QUE:</p>
  <p>El señor <strong>{nombre}</strong>, identificado con cédula de ciudadanía N.º {employee.documento}, laboró en el
  establecimiento <strong>{EMPRESA["nombre"]}</strong>, de propiedad de {EMPRESA["representante"]} (NIT {EMPRESA["nit"]}),
  mediante contrato individual de trabajo {employee.tipo_contrato}, desde el {_fecha_larga(employee.fecha_ingreso)} hasta el
  {_fecha_larga(fecha_retiro)}, desempeñando el cargo de <strong>{employee.cargo}</strong>, con un salario básico mensual de
  {_money(liq["salario_base"])} más el auxilio de transporte de ley.</p>
  <p>La presente certificación se expide a solicitud del interesado, en {EMPRESA["ciudad"]}, el {_fecha_larga(fecha_documento)}.</p>
  <div class="firma-sola"><strong>{EMPRESA["representante"]}</strong><br/>C.C. {EMPRESA["cedula_representante"]}<br/>Empleador · {EMPRESA["telefono"]}</div>
  {footer}
</div>

</body></html>"""


def correo_liquidacion_html(*, employee, liq: dict, fecha_retiro: date) -> str:
    """Cuerpo del correo que acompaña la liquidación final."""
    td = "padding:4px 12px 4px 0;color:#57534e"
    tv = "padding:4px 0;text-align:right"
    return f"""
    <div style="font-family:Arial,sans-serif;color:#1c1917;max-width:560px">
      <h2 style="color:#0d4a45;margin-bottom:4px">Liquidación definitiva de tu contrato</h2>
      <p>Hola {employee.nombre.split(" ")[0]},</p>
      <p>Como lo hablamos, tu contrato con Bigotes y Paticas terminó el
      <strong>{_fecha_larga(fecha_retiro)}</strong>. Tu salario quedó pagado hasta ese día y aquí
      está la liquidación de tus prestaciones por los {liq["dias_laborados"]} días que trabajaste con nosotros:</p>
      <table style="border-collapse:collapse;font-size:14px">
        <tr><td style="{td}">Cesantías</td><td style="{tv}">{_money(liq["cesantias"])}</td></tr>
        <tr><td style="{td}">Intereses a las cesantías</td><td style="{tv}">{_money(liq["intereses_cesantias"])}</td></tr>
        <tr><td style="{td}">Prima de servicios</td><td style="{tv}">{_money(liq["prima"])}</td></tr>
        <tr><td style="{td}">Vacaciones no disfrutadas</td><td style="{tv}">{_money(liq["vacaciones"])}</td></tr>
        <tr><td style="padding:6px 12px 6px 0;font-weight:bold;border-top:1px solid #d6d3d1">Total a pagar</td><td style="padding:6px 0;text-align:right;font-weight:bold;border-top:1px solid #d6d3d1">{_money(liq["total"])}</td></tr>
      </table>
      <p style="margin-top:16px">En el PDF adjunto van cuatro documentos: la carta de terminación, la
      liquidación con el cálculo de cada valor, el acta de terminación con paz y salvo y tu certificado laboral.
      Te pedimos firmar el acta y la liquidación y devolvérnoslas (en la tienda o por foto a este correo).</p>
      <p>Gracias por tu trabajo con nosotros, {employee.nombre.split(" ")[0]}. Te deseamos lo mejor con tu familia;
      aquí tienes las puertas abiertas.</p>
      <p>Diego Mauricio García<br/>Bigotes y Paticas</p>
      <p style="color:#78716c;font-size:12px">Bigotes y Paticas · Samara Plaza Mall, Local 2 · Dosquebradas · {EMPRESA["telefono"]}</p>
    </div>"""
