"""Desprendible de nómina y contrato de trabajo en PDF (WeasyPrint, 15-oct-2026).

Mismo motor y misma identidad que el comprobante de venta (`invoice_pdf`): el
logo va embebido en base64 y el PDF se arma desde las cifras congeladas del pago,
así que un desprendible de hace un año se vuelve a generar idéntico.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.invoice_pdf import LOGO_PNG_B64, generate_invoice_pdf

# Datos del empleador. Son los mismos que publica la web (business-info.ts) y la
# política de privacidad del store: persona natural, Régimen Simple.
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
