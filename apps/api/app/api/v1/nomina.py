"""Nómina quincenal: liquidar, pagar, desprendible por correo y contrato (15-oct-2026).

Diego: *"un botón que diga pagar nómina quincena y eso haga todo el ejercicio
interno contable hacia los gastos, manda el correo con el desprendible, deja el
registro del pago [...] yo veo el valor de la liquidación, le consigno al empleado
y el admin registra el pago cuando yo le dé al botón"*.

EL BOTÓN HACE CUATRO COSAS EN ESTE ORDEN, Y POR QUÉ EN ESTE ORDEN:

1. Vuelve a liquidar en el servidor (nunca se confía en los números que manda el
   navegador) y guarda la quincena con sus cifras congeladas.
2. Crea los dos gastos en `finance.expenses`: el neto consignado y la provisión de
   prestaciones. Van en la MISMA transacción que el pago: o queda todo o no queda
   nada.
3. Solo después de confirmar en la base, genera el PDF y manda el correo. Si el
   correo falla, el pago ya está hecho (la plata ya salió) y queda marcado con el
   error para reenviarlo desde el historial.
4. Devuelve el registro al admin.

Una quincena no se puede pagar dos veces: hay restricción única por empleado y
período, y el sistema solo ofrece la siguiente quincena sin pagar.
"""

from __future__ import annotations

import asyncio
import io
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from app.deps import CurrentUser, DBSession, require_permission
from app.models.finance import Employee, Expense, Payroll, PayrollParam, PayrollSettlement
from app.services import nomina as calc
from app.services.email import STORE_EMAIL, send_email
from app.services.nomina_pdf import (
    correo_liquidacion_html,
    html_a_pdf,
    render_contrato_html,
    render_desprendible_html,
    render_liquidacion_html,
)

log = structlog.get_logger()
router = APIRouter(prefix="/nomina", tags=["nomina"])

_BOGOTA = ZoneInfo("America/Bogota")


def _hoy() -> date:
    return datetime.now(_BOGOTA).date()


def _cop(v) -> str:
    """$ 929.965 — separador de miles colombiano, sin decimales."""
    return "$ " + f"{int(Decimal(str(v)).quantize(Decimal('1'))):,}".replace(",", ".")


# ────────────────── Schemas ──────────────────────


class EmployeeIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    documento: str = Field(min_length=5, max_length=30)
    email: str | None = None
    cargo: str = Field(default="Auxiliar", max_length=80)
    fecha_ingreso: date
    fecha_retiro: date | None = None
    salario_base: float | None = Field(default=None, ge=0)
    aux_transporte: float | None = Field(default=None, ge=0)
    tipo_contrato: str = "indefinido"
    activo: bool = True
    notas: str | None = None


class ParamIn(BaseModel):
    vigencia_desde: date
    smmlv: float = Field(gt=0)
    aux_transporte: float = Field(ge=0)
    pct_salud: float = Field(default=4, ge=0, le=100)
    pct_pension: float = Field(default=4, ge=0, le=100)
    fuente: str | None = None


class PagarIn(BaseModel):
    employee_id: uuid.UUID
    #: Clave del período que el admin vio en pantalla (p. ej. 2026-10-Q1). Se
    #: compara con la siguiente quincena pendiente: si no coincide, alguien pagó
    #: entre tanto y se rechaza para no pagar dos veces.
    periodo_clave: str
    dias_trabajados: int = Field(ge=0, le=15)
    otros_devengados: float = Field(default=0, ge=0)
    otros_descuentos: float = Field(default=0, ge=0)
    descripcion_otros: str | None = None
    metodo_pago: str = "Transferencia"
    banco_origen: str | None = None
    fecha_pago: date | None = None
    enviar_correo: bool = True


# ────────────────── Helpers ──────────────────────


async def _param_vigente(db: DBSession, fecha: date) -> PayrollParam:
    row = (
        await db.execute(
            select(PayrollParam)
            .where(PayrollParam.vigencia_desde <= fecha)
            .order_by(PayrollParam.vigencia_desde.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=409,
            detail="No hay salario mínimo configurado para esa fecha. Regístralo en Parámetros.",
        )
    return row


def _bases(emp: Employee, param: PayrollParam) -> tuple[Decimal, Decimal]:
    """Salario y auxilio mensuales que aplican: los del empleado o el mínimo vigente."""
    salario = Decimal(emp.salario_base) if emp.salario_base is not None else Decimal(param.smmlv)
    aux = (
        Decimal(emp.aux_transporte)
        if emp.aux_transporte is not None
        else Decimal(param.aux_transporte)
    )
    return salario, aux


async def _ultimo_pago(db: DBSession, employee_id: uuid.UUID) -> Payroll | None:
    return (
        await db.execute(
            select(Payroll)
            .where(Payroll.employee_id == employee_id)
            .order_by(Payroll.periodo_inicio.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _periodo_pendiente(db: DBSession, emp: Employee) -> calc.Periodo:
    ultimo = await _ultimo_pago(db, emp.id)
    if ultimo is None:
        return calc.periodo_que_contiene(emp.fecha_ingreso)
    return calc.periodo_siguiente(calc.periodo_que_contiene(ultimo.periodo_inicio))


def _periodo_out(p: calc.Periodo) -> dict:
    return {
        "inicio": p.inicio.isoformat(),
        "fin": p.fin.isoformat(),
        "quincena": p.quincena,
        "etiqueta": p.etiqueta,
        "clave": p.clave,
    }


def _employee_out(emp: Employee, param: PayrollParam) -> dict:
    salario, aux = _bases(emp, param)
    return {
        "id": str(emp.id),
        "nombre": emp.nombre,
        "documento": emp.documento,
        "email": emp.email,
        "cargo": emp.cargo,
        "fecha_ingreso": emp.fecha_ingreso.isoformat(),
        "fecha_retiro": emp.fecha_retiro.isoformat() if emp.fecha_retiro else None,
        "salario_base": float(salario),
        "aux_transporte": float(aux),
        "usa_minimo": emp.salario_base is None,
        "tipo_contrato": emp.tipo_contrato,
        "activo": emp.activo,
        "notas": emp.notas,
        "contrato_enviado_at": emp.contrato_enviado_at.isoformat()
        if emp.contrato_enviado_at
        else None,
        "contrato_enviado_a": emp.contrato_enviado_a,
        "provision_mensual": calc.provision_mensual(salario, aux),
    }


def _pago_out(p: Payroll, emp: Employee | None = None) -> dict:
    per = calc.periodo_que_contiene(p.periodo_inicio)
    return {
        "id": str(p.id),
        "consecutivo": p.consecutivo,
        "employee_id": str(p.employee_id),
        "employee_nombre": emp.nombre if emp else None,
        "periodo": _periodo_out(per),
        "dias_trabajados": p.dias_trabajados,
        "salario_base": float(p.salario_base),
        "aux_base": float(p.aux_base),
        "dev_salario": float(p.dev_salario),
        "dev_auxilio": float(p.dev_auxilio),
        "otros_devengados": float(p.otros_devengados),
        "total_devengado": float(p.total_devengado),
        "ded_salud": float(p.ded_salud),
        "ded_pension": float(p.ded_pension),
        "otros_descuentos": float(p.otros_descuentos),
        "descripcion_otros": p.descripcion_otros,
        "total_deducciones": float(p.total_deducciones),
        "neto": float(p.neto),
        "prov_cesantias": float(p.prov_cesantias),
        "prov_intereses": float(p.prov_intereses),
        "prov_prima": float(p.prov_prima),
        "prov_vacaciones": float(p.prov_vacaciones),
        "total_provision": float(p.total_provision),
        "fecha_pago": p.fecha_pago.isoformat(),
        "pagada_at": p.pagada_at.isoformat() if p.pagada_at else None,
        "pagada_por": p.pagada_por,
        "metodo_pago": p.metodo_pago,
        "banco_origen": p.banco_origen,
        "email_enviado_a": p.email_enviado_a,
        "email_enviado_at": p.email_enviado_at.isoformat() if p.email_enviado_at else None,
        "email_error": p.email_error,
    }


def _liquidar_para(
    emp: Employee,
    param: PayrollParam,
    dias: int,
    otros_devengados: float = 0,
    otros_descuentos: float = 0,
) -> calc.Liquidacion:
    salario, aux = _bases(emp, param)
    return calc.liquidar(
        salario_mensual=salario,
        aux_mensual=aux,
        pct_salud=Decimal(param.pct_salud),
        pct_pension=Decimal(param.pct_pension),
        dias=dias,
        smmlv=Decimal(param.smmlv),
        otros_devengados=Decimal(str(otros_devengados or 0)),
        otros_descuentos=Decimal(str(otros_descuentos or 0)),
    )


async def _pendiente_out(db: DBSession, emp: Employee) -> dict:
    per = await _periodo_pendiente(db, emp)
    param = await _param_vigente(db, per.inicio)
    dias = calc.dias_laborales(per, emp.fecha_ingreso, emp.fecha_retiro)
    liq = _liquidar_para(emp, param, dias)
    hoy = _hoy()
    puede, motivo = True, None
    if not emp.activo:
        puede, motivo = False, "El empleado está inactivo."
    elif per.inicio > hoy:
        puede, motivo = False, f"La quincena del {per.etiqueta} todavía no empieza."
    elif dias == 0:
        puede, motivo = False, "No hay días trabajados en esta quincena."
    return {
        "periodo": _periodo_out(per),
        "dias_sugeridos": dias,
        "quincena_terminada": per.fin <= hoy,
        "puede_pagar": puede,
        "motivo": motivo,
        "liquidacion": liq.as_dict(),
    }


def _desprendible_pdf(pago: Payroll, emp: Employee) -> bytes:
    per = calc.periodo_que_contiene(pago.periodo_inicio)
    html = render_desprendible_html(payroll=pago, employee=emp, periodo_etiqueta=per.etiqueta)
    return html_a_pdf(html)


async def _enviar_desprendible(db: DBSession, pago: Payroll, emp: Employee) -> bool:
    """Genera el PDF y lo manda; deja el resultado en el registro del pago."""
    if not emp.email:
        pago.email_error = "El empleado no tiene correo registrado."
        await db.commit()
        return False
    per = calc.periodo_que_contiene(pago.periodo_inicio)
    try:
        pdf = await asyncio.to_thread(_desprendible_pdf, pago, emp)
        html = f"""
        <div style="font-family:Arial,sans-serif;color:#1c1917;max-width:560px">
          <h2 style="color:#0d4a45;margin-bottom:4px">Desprendible de nómina</h2>
          <p>Hola {emp.nombre.split(" ")[0]},</p>
          <p>Adjunto encuentras el desprendible de pago de la quincena del
          <strong>{per.etiqueta}</strong>.</p>
          <table style="border-collapse:collapse;font-size:14px">
            <tr><td style="padding:4px 12px 4px 0;color:#57534e">Total devengado</td><td style="padding:4px 0;text-align:right">{_cop(pago.total_devengado)}</td></tr>
            <tr><td style="padding:4px 12px 4px 0;color:#57534e">Deducciones (salud y pensión)</td><td style="padding:4px 0;text-align:right">- {_cop(pago.total_deducciones)}</td></tr>
            <tr><td style="padding:6px 12px 6px 0;font-weight:bold;border-top:1px solid #d6d3d1">Neto pagado</td><td style="padding:6px 0;text-align:right;font-weight:bold;border-top:1px solid #d6d3d1">{_cop(pago.neto)}</td></tr>
          </table>
          <p style="margin-top:16px">Pago realizado el {pago.fecha_pago.strftime("%d/%m/%Y")} por {pago.metodo_pago}.</p>
          <p style="color:#78716c;font-size:12px">Bigotes y Paticas · Samara Plaza Mall, Local 2 · Dosquebradas</p>
        </div>"""
        ok = await asyncio.to_thread(
            send_email,
            emp.email,
            f"Desprendible de nómina · {per.etiqueta}",
            html,
            "",
            [(f"desprendible-{pago.consecutivo:05d}.pdf", pdf, "application/pdf")],
            [STORE_EMAIL],
        )
    except Exception as exc:  # pragma: no cover - red/pdf
        log.error("nomina.email_error", pago=str(pago.id), error=str(exc))
        ok = False
        pago.email_error = str(exc)[:500]
    if ok:
        pago.email_enviado_a = emp.email
        pago.email_enviado_at = datetime.now(UTC)
        pago.email_error = None
    elif not pago.email_error:
        pago.email_error = "El servicio de correo rechazó el envío."
    await db.commit()
    return ok


# ────────────────── Endpoints ──────────────────────


@router.get("/resumen", dependencies=[Depends(require_permission("finance:read"))])
async def resumen(db: DBSession, user: CurrentUser):
    """Todo lo que la pantalla de nómina necesita en una sola llamada."""
    hoy = _hoy()
    param = await _param_vigente(db, hoy)
    empleados = (
        (await db.execute(select(Employee).order_by(Employee.activo.desc(), Employee.nombre)))
        .scalars()
        .all()
    )
    out_emps = []
    for emp in empleados:
        d = _employee_out(emp, param)
        d["pendiente"] = await _pendiente_out(db, emp) if emp.activo else None
        liqf = (
            await db.execute(select(PayrollSettlement).where(PayrollSettlement.employee_id == emp.id))
        ).scalar_one_or_none()
        d["liquidacion_final"] = _settlement_out(liqf) if liqf else None
        acum = (
            await db.execute(
                text("""
                    SELECT coalesce(sum(prov_cesantias),0) AS ces,
                           coalesce(sum(prov_intereses),0) AS inte,
                           coalesce(sum(prov_prima),0) AS prima,
                           coalesce(sum(prov_vacaciones),0) AS vac,
                           coalesce(sum(total_provision),0) AS total,
                           coalesce(sum(neto),0) AS neto,
                           count(*) AS n
                    FROM finance.payrolls WHERE employee_id = :e
                """),
                {"e": emp.id},
            )
        ).one()
        d["acumulado"] = {
            "quincenas_pagadas": int(acum.n),
            "neto_pagado": float(acum.neto),
            "provision": {
                "cesantias": float(acum.ces),
                "intereses_cesantias": float(acum.inte),
                "prima": float(acum.prima),
                "vacaciones": float(acum.vac),
                "total": float(acum.total),
            },
        }
        out_emps.append(d)

    pagos = (
        (
            await db.execute(
                select(Payroll, Employee)
                .join(Employee, Employee.id == Payroll.employee_id)
                .order_by(Payroll.periodo_inicio.desc(), Payroll.consecutivo.desc())
                .limit(48)
            )
        )
        .all()
    )
    params = (
        (await db.execute(select(PayrollParam).order_by(PayrollParam.vigencia_desde.desc())))
        .scalars()
        .all()
    )
    return {
        "hoy": hoy.isoformat(),
        "parametros_vigentes": {
            "vigencia_desde": param.vigencia_desde.isoformat(),
            "smmlv": float(param.smmlv),
            "aux_transporte": float(param.aux_transporte),
            "pct_salud": float(param.pct_salud),
            "pct_pension": float(param.pct_pension),
            "fuente": param.fuente,
        },
        "parametros": [
            {
                "id": str(p.id),
                "vigencia_desde": p.vigencia_desde.isoformat(),
                "smmlv": float(p.smmlv),
                "aux_transporte": float(p.aux_transporte),
                "pct_salud": float(p.pct_salud),
                "pct_pension": float(p.pct_pension),
                "fuente": p.fuente,
            }
            for p in params
        ],
        "empleados": out_emps,
        "historial": [_pago_out(p, e) for p, e in pagos],
    }


@router.get("/liquidacion", dependencies=[Depends(require_permission("finance:read"))])
async def liquidacion(
    db: DBSession,
    user: CurrentUser,
    employee_id: uuid.UUID,
    dias: int = Query(15, ge=0, le=15),
    otros_devengados: float = Query(0, ge=0),
    otros_descuentos: float = Query(0, ge=0),
):
    """Vista previa de la quincena pendiente con los ajustes que el admin escribe."""
    emp = await db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    per = await _periodo_pendiente(db, emp)
    param = await _param_vigente(db, per.inicio)
    liq = _liquidar_para(emp, param, dias, otros_devengados, otros_descuentos)
    return {"periodo": _periodo_out(per), "liquidacion": liq.as_dict()}


@router.post("/pagar", dependencies=[Depends(require_permission("finance:write"))])
async def pagar(payload: PagarIn, db: DBSession, user: CurrentUser):
    emp = await db.get(Employee, payload.employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if not emp.activo:
        raise HTTPException(status_code=409, detail="El empleado está inactivo")

    per = await _periodo_pendiente(db, emp)
    if per.clave != payload.periodo_clave:
        raise HTTPException(
            status_code=409,
            detail=f"La quincena pendiente ahora es la del {per.etiqueta}. Recarga la página.",
        )
    hoy = _hoy()
    if per.inicio > hoy:
        raise HTTPException(status_code=409, detail="Esa quincena todavía no empieza.")
    if payload.dias_trabajados == 0:
        raise HTTPException(status_code=422, detail="Los días trabajados no pueden ser cero.")

    param = await _param_vigente(db, per.inicio)
    liq = _liquidar_para(
        emp, param, payload.dias_trabajados, payload.otros_devengados, payload.otros_descuentos
    )
    if liq.neto <= 0:
        raise HTTPException(status_code=422, detail="El neto a pagar debe ser mayor que cero.")

    fecha_pago = payload.fecha_pago or hoy
    consecutivo = (
        await db.execute(text("SELECT nextval('finance.payrolls_consecutivo_seq')"))
    ).scalar_one()

    # 1 y 2 — el pago y sus dos gastos, en una sola transacción.
    gasto = Expense(
        fecha=fecha_pago,
        monto=liq.neto,
        categoria="Nómina",
        tipo="Operativo",
        descripcion=f"Nómina {emp.nombre} · quincena {per.etiqueta}",
        metodo_pago=payload.metodo_pago,
        banco_origen=payload.banco_origen or None,
        es_fijo=True,
        created_by=user.email,
        legacy_id=f"NOMINA-{consecutivo:05d}",
    )
    provision = Expense(
        fecha=fecha_pago,
        monto=liq.total_provision,
        categoria="Nómina",
        tipo="Operativo",
        descripcion=(
            f"Provisión prestaciones {emp.nombre} · quincena {per.etiqueta} "
            f"(cesantías, intereses, prima, vacaciones)"
        ),
        metodo_pago="Provisión",
        banco_origen=None,
        es_fijo=True,
        created_by=user.email,
        legacy_id=f"NOMINA-PROV-{consecutivo:05d}",
    )
    db.add_all([gasto, provision])
    await db.flush()

    pago = Payroll(
        consecutivo=int(consecutivo),
        employee_id=emp.id,
        periodo_inicio=per.inicio,
        periodo_fin=per.fin,
        quincena=per.quincena,
        dias_trabajados=liq.dias_trabajados,
        salario_base=liq.salario_base,
        aux_base=liq.aux_base,
        pct_salud=liq.pct_salud,
        pct_pension=liq.pct_pension,
        dev_salario=liq.dev_salario,
        dev_auxilio=liq.dev_auxilio,
        otros_devengados=liq.otros_devengados,
        total_devengado=liq.total_devengado,
        ded_salud=liq.ded_salud,
        ded_pension=liq.ded_pension,
        otros_descuentos=liq.otros_descuentos,
        descripcion_otros=payload.descripcion_otros or None,
        total_deducciones=liq.total_deducciones,
        neto=liq.neto,
        prov_cesantias=liq.prov_cesantias,
        prov_intereses=liq.prov_intereses,
        prov_prima=liq.prov_prima,
        prov_vacaciones=liq.prov_vacaciones,
        total_provision=liq.total_provision,
        estado="pagada",
        fecha_pago=fecha_pago,
        pagada_at=datetime.now(UTC),
        pagada_por=user.email,
        metodo_pago=payload.metodo_pago,
        banco_origen=payload.banco_origen or None,
        expense_id=gasto.id,
        provision_expense_id=provision.id,
    )
    db.add(pago)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        if "uq_payrolls_employee_periodo" in str(exc) or "payrolls_employee_id_periodo" in str(exc):
            raise HTTPException(status_code=409, detail="Esa quincena ya está pagada.") from exc
        raise
    await db.refresh(pago)
    log.info("nomina.pagada", consecutivo=consecutivo, empleado=emp.nombre, neto=float(liq.neto))

    # 3 — el correo, después de que la plata ya quedó registrada.
    if payload.enviar_correo:
        await _enviar_desprendible(db, pago, emp)
        await db.refresh(pago)

    return _pago_out(pago, emp)


@router.get(
    "/pagos/{pago_id}/desprendible.pdf",
    dependencies=[Depends(require_permission("finance:read"))],
)
async def desprendible_pdf(pago_id: uuid.UUID, db: DBSession, user: CurrentUser):
    pago = await db.get(Payroll, pago_id)
    if pago is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    emp = await db.get(Employee, pago.employee_id)
    pdf = await asyncio.to_thread(_desprendible_pdf, pago, emp)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="desprendible-{pago.consecutivo:05d}.pdf"'
        },
    )


@router.post(
    "/pagos/{pago_id}/reenviar", dependencies=[Depends(require_permission("finance:write"))]
)
async def reenviar_desprendible(pago_id: uuid.UUID, db: DBSession, user: CurrentUser):
    pago = await db.get(Payroll, pago_id)
    if pago is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    emp = await db.get(Employee, pago.employee_id)
    ok = await _enviar_desprendible(db, pago, emp)
    await db.refresh(pago)
    if not ok:
        raise HTTPException(status_code=502, detail=pago.email_error or "No se pudo enviar")
    return _pago_out(pago, emp)


# ── Empleados ──


@router.post("/empleados", dependencies=[Depends(require_permission("finance:write"))])
async def crear_empleado(payload: EmployeeIn, db: DBSession, user: CurrentUser):
    existe = (
        await db.execute(select(Employee).where(Employee.documento == payload.documento.strip()))
    ).scalar_one_or_none()
    if existe:
        raise HTTPException(status_code=409, detail="Ya hay un empleado con esa cédula")
    emp = Employee(**_employee_fields(payload))
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return _employee_out(emp, await _param_vigente(db, _hoy()))


@router.put("/empleados/{employee_id}", dependencies=[Depends(require_permission("finance:write"))])
async def editar_empleado(
    employee_id: uuid.UUID, payload: EmployeeIn, db: DBSession, user: CurrentUser
):
    emp = await db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    for k, v in _employee_fields(payload).items():
        setattr(emp, k, v)
    emp.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(emp)
    return _employee_out(emp, await _param_vigente(db, _hoy()))


def _employee_fields(p: EmployeeIn) -> dict:
    return {
        "nombre": p.nombre.strip(),
        "documento": p.documento.strip(),
        "email": (p.email or "").strip() or None,
        "cargo": p.cargo.strip() or "Auxiliar",
        "fecha_ingreso": p.fecha_ingreso,
        "fecha_retiro": p.fecha_retiro,
        "salario_base": Decimal(str(p.salario_base)) if p.salario_base else None,
        "aux_transporte": Decimal(str(p.aux_transporte))
        if p.aux_transporte is not None and p.salario_base
        else None,
        "tipo_contrato": p.tipo_contrato or "indefinido",
        "activo": p.activo,
        "notas": (p.notas or "").strip() or None,
    }


def _contrato_pdf(emp: Employee, param: PayrollParam) -> bytes:
    salario, aux = _bases(emp, param)
    return html_a_pdf(render_contrato_html(employee=emp, smmlv=salario, aux=aux))


@router.get(
    "/empleados/{employee_id}/contrato.pdf",
    dependencies=[Depends(require_permission("finance:read"))],
)
async def contrato_pdf(employee_id: uuid.UUID, db: DBSession, user: CurrentUser):
    emp = await db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    param = await _param_vigente(db, emp.fecha_ingreso)
    pdf = await asyncio.to_thread(_contrato_pdf, emp, param)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="contrato-{emp.documento}.pdf"'},
    )


@router.post(
    "/empleados/{employee_id}/contrato/enviar",
    dependencies=[Depends(require_permission("finance:write"))],
)
async def enviar_contrato(employee_id: uuid.UUID, db: DBSession, user: CurrentUser):
    """Manda el contrato al correo del empleado con copia a la tienda (constancia)."""
    emp = await db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if not emp.email:
        raise HTTPException(status_code=422, detail="El empleado no tiene correo registrado")
    param = await _param_vigente(db, emp.fecha_ingreso)
    pdf = await asyncio.to_thread(_contrato_pdf, emp, param)
    html = f"""
    <div style="font-family:Arial,sans-serif;color:#1c1917;max-width:560px">
      <h2 style="color:#0d4a45;margin-bottom:4px">Contrato de trabajo</h2>
      <p>Hola {emp.nombre.split(" ")[0]},</p>
      <p>Adjunto encuentras tu contrato individual de trabajo con Bigotes y Paticas,
      con fecha de inicio el {emp.fecha_ingreso.strftime("%d/%m/%Y")}, para que lo conserves
      como constancia.</p>
      <p>Cualquier duda, escríbenos o háblanos en la tienda.</p>
      <p style="color:#78716c;font-size:12px">Bigotes y Paticas · Samara Plaza Mall, Local 2 · Dosquebradas</p>
    </div>"""
    ok = await asyncio.to_thread(
        send_email,
        emp.email,
        "Contrato de trabajo · Bigotes y Paticas",
        html,
        "",
        [(f"contrato-{emp.documento}.pdf", pdf, "application/pdf")],
        [STORE_EMAIL],
    )
    if not ok:
        raise HTTPException(status_code=502, detail="El servicio de correo rechazó el envío")
    emp.contrato_enviado_at = datetime.now(UTC)
    emp.contrato_enviado_a = emp.email
    await db.commit()
    await db.refresh(emp)
    return _employee_out(emp, await _param_vigente(db, _hoy()))


# ── Parámetros legales ──


@router.post("/parametros", dependencies=[Depends(require_permission("finance:write"))])
async def guardar_parametro(payload: ParamIn, db: DBSession, user: CurrentUser):
    """Crea o actualiza el mínimo de una vigencia (una fila por fecha de vigencia)."""
    row = (
        await db.execute(
            select(PayrollParam).where(PayrollParam.vigencia_desde == payload.vigencia_desde)
        )
    ).scalar_one_or_none()
    if row is None:
        row = PayrollParam(vigencia_desde=payload.vigencia_desde)
        db.add(row)
    row.smmlv = Decimal(str(payload.smmlv))
    row.aux_transporte = Decimal(str(payload.aux_transporte))
    row.pct_salud = Decimal(str(payload.pct_salud))
    row.pct_pension = Decimal(str(payload.pct_pension))
    row.fuente = (payload.fuente or "").strip() or None
    await db.commit()
    return {"ok": True}


# ── Liquidación final (17-nov-2026) ──
#
# Diego: *"necesito calcularle la liquidación con carta formal y con cierre de
# contrato formal [...] y que me quede registro de todo"*. Registrar hace tres
# cosas en una transacción: congela la liquidación, retira al empleado (inactivo
# con fecha de retiro) y cuadra la provisión. La provisión quincenal ya llevó las
# prestaciones al gasto; si sobra, se descuenta de la última provisión; si falta,
# se registra un gasto por la diferencia. Pagar la liquidación no es gasto nuevo.


class LiquidacionFinalIn(BaseModel):
    fecha_retiro: date
    motivo: str = Field(default="mutuo_acuerdo", pattern="^(mutuo_acuerdo|renuncia)$")
    razon: str | None = "a solicitud del trabajador por motivos familiares"
    metodo_pago: str = "Transferencia"
    fecha_pago: date | None = None
    enviar_correo: bool = False


def _settlement_out(s: PayrollSettlement) -> dict:
    return {
        "id": str(s.id),
        "consecutivo": s.consecutivo,
        "fecha_retiro": s.fecha_retiro.isoformat(),
        "fecha_documento": s.fecha_documento.isoformat(),
        "motivo": s.motivo,
        "razon": s.razon,
        "detalle": s.detalle,
        "total": float(s.total),
        "provision_acumulada": float(s.provision_acumulada),
        "ajuste_provision": float(s.ajuste_provision),
        "metodo_pago": s.metodo_pago,
        "fecha_pago": s.fecha_pago.isoformat() if s.fecha_pago else None,
        "registrada_por": s.registrada_por,
        "email_enviado_a": s.email_enviado_a,
        "email_enviado_at": s.email_enviado_at.isoformat() if s.email_enviado_at else None,
        "email_error": s.email_error,
    }


async def _calcular_final(db: DBSession, emp: Employee, fecha_retiro: date) -> dict:
    if fecha_retiro < emp.fecha_ingreso:
        raise HTTPException(status_code=422, detail="La fecha de retiro es anterior al ingreso.")
    param = await _param_vigente(db, fecha_retiro)
    salario, aux = _bases(emp, param)
    liq = calc.liquidacion_final(
        salario_mensual=salario,
        aux_mensual=aux,
        fecha_ingreso=emp.fecha_ingreso,
        fecha_retiro=fecha_retiro,
        smmlv=Decimal(param.smmlv),
    )
    pagos = (
        (
            await db.execute(
                select(Payroll).where(Payroll.employee_id == emp.id).order_by(Payroll.periodo_inicio)
            )
        )
        .scalars()
        .all()
    )
    falta_salario = None
    if calc.dias_360(emp.fecha_ingreso, fecha_retiro) > sum(p.dias_trabajados for p in pagos):
        falta_salario = "Hay días sin pagar: liquida primero la última quincena con el botón de siempre."
    provision = sum((Decimal(p.total_provision) for p in pagos), Decimal(0))
    return {
        "liquidacion": liq,
        "pagos": pagos,
        "provision_acumulada": float(provision),
        "ajuste_provision": float(Decimal(str(liq["total"])) - provision),
        "aviso": falta_salario,
    }


def _liquidacion_pdf(s: PayrollSettlement, emp: Employee, pagos: list) -> bytes:
    html = render_liquidacion_html(
        employee=emp,
        liq=s.detalle,
        fecha_retiro=s.fecha_retiro,
        fecha_documento=s.fecha_documento,
        motivo=s.motivo,
        razon=s.razon or "",
        pagos=pagos,
        consecutivo=s.consecutivo,
    )
    return html_a_pdf(html)


async def _pagos_de(db: DBSession, employee_id: uuid.UUID) -> list:
    return list(
        (
            await db.execute(
                select(Payroll)
                .where(Payroll.employee_id == employee_id)
                .order_by(Payroll.periodo_inicio)
            )
        )
        .scalars()
        .all()
    )


async def _enviar_liquidacion(db: DBSession, s: PayrollSettlement, emp: Employee) -> bool:
    if not emp.email:
        s.email_error = "El empleado no tiene correo registrado."
        await db.commit()
        return False
    try:
        pagos = await _pagos_de(db, emp.id)
        pdf = await asyncio.to_thread(_liquidacion_pdf, s, emp, pagos)
        ok = await asyncio.to_thread(
            send_email,
            emp.email,
            "Liquidación definitiva de tu contrato · Bigotes y Paticas",
            correo_liquidacion_html(employee=emp, liq=s.detalle, fecha_retiro=s.fecha_retiro),
            "",
            [(f"liquidacion-L-{s.consecutivo:05d}.pdf", pdf, "application/pdf")],
            [STORE_EMAIL],
        )
    except Exception as exc:  # pragma: no cover - red/pdf
        log.error("nomina.liquidacion_email_error", error=str(exc))
        ok = False
        s.email_error = str(exc)[:500]
    if ok:
        s.email_enviado_a = emp.email
        s.email_enviado_at = datetime.now(UTC)
        s.email_error = None
    elif not s.email_error:
        s.email_error = "El servicio de correo rechazó el envío."
    await db.commit()
    return ok


@router.get(
    "/empleados/{employee_id}/liquidacion-final",
    dependencies=[Depends(require_permission("finance:read"))],
)
async def liquidacion_final_preview(
    employee_id: uuid.UUID, fecha_retiro: date, db: DBSession, user: CurrentUser
):
    emp = await db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    r = await _calcular_final(db, emp, fecha_retiro)
    r.pop("pagos")
    return r


@router.post(
    "/empleados/{employee_id}/liquidacion-final",
    dependencies=[Depends(require_permission("finance:write"))],
)
async def liquidacion_final_registrar(
    employee_id: uuid.UUID, payload: LiquidacionFinalIn, db: DBSession, user: CurrentUser
):
    emp = await db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    ya = (
        await db.execute(select(PayrollSettlement).where(PayrollSettlement.employee_id == emp.id))
    ).scalar_one_or_none()
    if ya is not None:
        raise HTTPException(status_code=409, detail="Este empleado ya tiene la liquidación final registrada.")
    r = await _calcular_final(db, emp, payload.fecha_retiro)
    if r["aviso"]:
        raise HTTPException(status_code=409, detail=r["aviso"])
    liq = r["liquidacion"]
    total = Decimal(str(liq["total"]))
    ajuste = Decimal(str(r["ajuste_provision"]))
    hoy = _hoy()
    consecutivo = (
        await db.execute(text("SELECT coalesce(max(consecutivo), 0) + 1 FROM finance.payroll_settlements"))
    ).scalar_one()

    ajuste_id = None
    if ajuste > 0:
        # Faltó provisión: el faltante sí es gasto.
        g = Expense(
            fecha=payload.fecha_pago or hoy,
            monto=ajuste,
            categoria="Nómina",
            tipo="Operativo",
            descripcion=f"Ajuste provisión · liquidación final L-{consecutivo:05d} {emp.nombre}",
            metodo_pago="Provisión",
            es_fijo=False,
            created_by=user.email,
            legacy_id=f"NOMINA-LIQ-{consecutivo:05d}",
        )
        db.add(g)
        await db.flush()
        ajuste_id = g.id
    elif ajuste < 0:
        # Sobró provisión: se devuelve descontándola de las provisiones, de la más reciente hacia atrás.
        sobra = -ajuste
        for p in reversed(r["pagos"]):
            if sobra <= 0 or p.provision_expense_id is None:
                continue
            gasto = await db.get(Expense, p.provision_expense_id)
            if gasto is None:
                continue
            baja = min(sobra, Decimal(gasto.monto))
            gasto.monto = Decimal(gasto.monto) - baja
            gasto.descripcion = (
                f"{gasto.descripcion} · ajustada -{_cop(baja)} en la liquidación final "
                f"L-{consecutivo:05d} (la provisión quincenal superó lo liquidado)"
            )
            gasto.updated_at = datetime.now(UTC)
            ajuste_id = ajuste_id or gasto.id
            sobra -= baja

    s = PayrollSettlement(
        consecutivo=int(consecutivo),
        employee_id=emp.id,
        fecha_retiro=payload.fecha_retiro,
        fecha_documento=hoy,
        motivo=payload.motivo,
        razon=(payload.razon or "").strip() or None,
        detalle=liq,
        total=total,
        provision_acumulada=Decimal(str(r["provision_acumulada"])),
        ajuste_provision=ajuste,
        ajuste_expense_id=ajuste_id,
        metodo_pago=payload.metodo_pago,
        fecha_pago=payload.fecha_pago or hoy,
        registrada_por=user.email,
    )
    db.add(s)
    emp.fecha_retiro = payload.fecha_retiro
    emp.activo = False
    nota = f"Retirado el {payload.fecha_retiro:%d/%m/%Y} · liquidación final L-{consecutivo:05d} por {_cop(total)}."
    emp.notas = f"{emp.notas}\n{nota}" if emp.notas else nota
    emp.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(s)
    log.info("nomina.liquidacion_final", empleado=emp.nombre, total=float(total), ajuste=float(ajuste))
    if payload.enviar_correo:
        await _enviar_liquidacion(db, s, emp)
        await db.refresh(s)
    return _settlement_out(s)


@router.get(
    "/liquidaciones/{settlement_id}/pdf",
    dependencies=[Depends(require_permission("finance:read"))],
)
async def liquidacion_final_pdf(settlement_id: uuid.UUID, db: DBSession, user: CurrentUser):
    s = await db.get(PayrollSettlement, settlement_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Liquidación no encontrada")
    emp = await db.get(Employee, s.employee_id)
    pagos = await _pagos_de(db, emp.id)
    pdf = await asyncio.to_thread(_liquidacion_pdf, s, emp, pagos)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="liquidacion-L-{s.consecutivo:05d}.pdf"'},
    )


@router.post(
    "/liquidaciones/{settlement_id}/enviar",
    dependencies=[Depends(require_permission("finance:write"))],
)
async def liquidacion_final_enviar(settlement_id: uuid.UUID, db: DBSession, user: CurrentUser):
    s = await db.get(PayrollSettlement, settlement_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Liquidación no encontrada")
    emp = await db.get(Employee, s.employee_id)
    ok = await _enviar_liquidacion(db, s, emp)
    await db.refresh(s)
    if not ok:
        raise HTTPException(status_code=502, detail=s.email_error or "No se pudo enviar")
    return _settlement_out(s)
