'use client';

/**
 * Estados financieros (30-oct-2026): estado de resultados, balance a hoy, flujo de
 * caja, historial e indicadores. Todo sale de UN solo endpoint
 * (`/v1/finance/estados`) con UNA sola regla contable (app/services/contabilidad.py),
 * así el P&L de Analítica y el de Finanzas ya no pueden decir cosas distintas.
 */

import { useState } from 'react';
import {
  ResponsiveContainer, ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts';
import {
  ArrowUp, ArrowDown, ChevronDown, ChevronRight, AlertTriangle, Info, OctagonAlert,
  Scale, Banknote, CalendarRange, Gauge,
} from 'lucide-react';
import type { EstadosFinancieros, EstadoResultados } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

function mesCorto(ym: string) {
  const [y, m] = ym.split('-');
  return `${MESES[Number(m) - 1]} ${y.slice(2)}`;
}

function fechaCorta(iso: string) {
  const [y, m, d] = iso.split('-');
  return `${Number(d)} ${MESES[Number(m) - 1]} ${y}`;
}

const money = (v: number) => formatCurrency(v);
const pct = (v: number) => `${v.toLocaleString('es-CO', { maximumFractionDigits: 1 })}%`;

function Delta({ value, invert = false }: { value: number | null | undefined; invert?: boolean }) {
  if (value === null || value === undefined) return <span className="text-xs text-muted-foreground">sin base</span>;
  const good = invert ? value <= 0 : value >= 0;
  const Icon = value >= 0 ? ArrowUp : ArrowDown;
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${good ? 'text-emerald-600' : 'text-rose-600'}`}>
      <Icon className="w-3 h-3" /> {Math.abs(value).toLocaleString('es-CO', { maximumFractionDigits: 1 })}%
    </span>
  );
}

function tono(v: number) {
  return v >= 0 ? 'text-emerald-700' : 'text-rose-600';
}

// ─── KPIs ───────────────────────────────────────────────────────────────────

export function ResumenKpis({ data }: { data: EstadosFinancieros }) {
  const r = data.resultados;
  const v = data.variacion;
  const neta = r.utilidad_neta >= 0;
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Card className="p-4">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Ventas netas</p>
        <p className="text-2xl font-bold tabular-nums mt-1">{money(r.ventas_netas)}</p>
        <div className="flex items-center justify-between mt-1 text-xs text-muted-foreground">
          <span>{r.n_ventas.toLocaleString('es-CO')} ventas · ticket {money(r.ticket_promedio)}</span>
          <Delta value={v.ventas_netas} />
        </div>
      </Card>
      <Card className="p-4">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Utilidad bruta</p>
        <p className={`text-2xl font-bold tabular-nums mt-1 ${tono(r.utilidad_bruta)}`}>{money(r.utilidad_bruta)}</p>
        <div className="flex items-center justify-between mt-1 text-xs text-muted-foreground">
          <span>Margen {pct(r.margen_bruto_pct)} · antes {pct(data.anterior.margen_bruto_pct)}</span>
          <Delta value={v.utilidad_bruta} />
        </div>
      </Card>
      <Card className="p-4">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Gastos operativos</p>
        <p className="text-2xl font-bold tabular-nums mt-1 text-rose-600">{money(r.gastos_operativos)}</p>
        <div className="flex items-center justify-between mt-1 text-xs text-muted-foreground">
          <span>{pct(data.indicadores.gastos_sobre_ventas_pct)} de las ventas</span>
          <Delta value={v.gastos_operativos} invert />
        </div>
      </Card>
      <Card className={`p-4 border-2 ${neta ? 'bg-emerald-50 border-emerald-300' : 'bg-rose-50 border-rose-300'}`}>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Utilidad neta</p>
        <p className={`text-2xl font-bold tabular-nums mt-1 ${tono(r.utilidad_neta)}`}>{money(r.utilidad_neta)}</p>
        <div className="flex items-center justify-between mt-1 text-xs text-muted-foreground">
          <span>Margen neto {pct(r.margen_neto_pct)}</span>
          <Delta value={v.utilidad_neta} />
        </div>
      </Card>
    </div>
  );
}

// ─── Estado de resultados ────────────────────────────────────────────────────

type Fila = {
  label: string;
  value: number;
  prev?: number;
  kind?: 'resta' | 'total' | 'final' | 'nota';
  sub?: string;
  pctVentas?: boolean;
};

function FilaEstado({ f, ventas, mostrarAnterior }: { f: Fila; ventas: number; mostrarAnterior: boolean }) {
  const esResta = f.kind === 'resta';
  const esTotal = f.kind === 'total' || f.kind === 'final';
  const esFinal = f.kind === 'final';
  const esNota = f.kind === 'nota';
  const color = esResta ? 'text-rose-600' : esTotal ? tono(f.value) : '';
  return (
    <tr
      className={`${esTotal ? 'border-t-2 border-gray-300 bg-muted/30' : 'border-t border-dashed border-gray-200'} ${esFinal ? 'bg-emerald-50/60' : ''}`}
    >
      <td className={`py-2.5 pr-3 ${esNota ? 'pl-8 text-xs text-muted-foreground' : esTotal ? 'font-bold' : 'pl-4'} ${esFinal ? 'text-base' : 'text-sm'}`}>
        {esResta && <span className="text-rose-400 mr-1">(−)</span>}
        {esTotal && <span className="text-muted-foreground mr-1">=</span>}
        {f.label}
        {f.sub && <span className="ml-2 text-xs font-normal text-muted-foreground">{f.sub}</span>}
      </td>
      <td className={`py-2.5 text-right tabular-nums whitespace-nowrap ${esNota ? 'text-xs text-muted-foreground' : esFinal ? 'text-base font-bold' : esTotal ? 'font-bold' : 'text-sm'} ${color}`}>
        {esResta && f.value > 0 ? '− ' : ''}{money(f.value)}
      </td>
      <td className="py-2.5 pl-3 text-right text-xs text-muted-foreground tabular-nums w-16">
        {f.pctVentas !== false && !esNota && ventas > 0 ? pct((f.value / ventas) * 100) : ''}
      </td>
      {mostrarAnterior && (
        <td className={`py-2.5 pl-3 text-right text-xs tabular-nums whitespace-nowrap text-muted-foreground ${esTotal ? 'font-semibold' : ''}`}>
          {f.prev !== undefined ? money(f.prev) : ''}
        </td>
      )}
    </tr>
  );
}

export function EstadoResultadosCard({
  r, anterior, titulo = 'Estado de resultados',
}: { r: EstadoResultados; anterior?: EstadoResultados; titulo?: string }) {
  const [verGastos, setVerGastos] = useState(true);
  const mostrarAnterior = !!anterior;
  const a = anterior;
  const descuentos = r.descuentos;
  const filas: Fila[] = [
    { label: 'Ventas brutas', value: r.ventas_brutas, prev: a?.ventas_brutas, sub: `${r.n_ventas} ventas · ${r.unidades} unidades` },
    { label: 'Descuentos y bonos', value: descuentos, prev: a?.descuentos, kind: 'resta', sub: r.bonos_bienvenida ? `incluye bono de bienvenida ${money(r.bonos_bienvenida)}` : undefined },
    { label: 'Ventas netas', value: r.ventas_netas, prev: a?.ventas_netas, kind: 'total' },
    { label: 'Costo de la mercancía vendida', value: r.costo_ventas, prev: a?.costo_ventas, kind: 'resta', sub: 'costo congelado en cada venta, IVA incluido' },
    { label: 'Utilidad bruta', value: r.utilidad_bruta, prev: a?.utilidad_bruta, kind: 'total', sub: `margen ${pct(r.margen_bruto_pct)}` },
  ];
  const filasGastos: Fila[] = r.gastos_por_categoria.map((g) => ({
    label: `${g.categoria} · ${g.es_fijo ? 'fijo' : 'variable'} · ${g.n} ${g.n === 1 ? 'registro' : 'registros'}`,
    value: g.total,
    prev: a?.gastos_por_categoria.find((x) => x.categoria === g.categoria)?.total,
    kind: 'nota',
  }));
  const filasFinal: Fila[] = [
    { label: 'Utilidad operacional', value: r.utilidad_operacional, prev: a?.utilidad_operacional, kind: 'total', sub: `margen ${pct(r.margen_operacional_pct)}` },
    { label: 'Comisión del datáfono', value: r.comision_tarjeta, prev: a?.comision_tarjeta, kind: 'resta', sub: `estimada sobre ${money(r.ventas_tarjeta)} en tarjeta` },
    { label: 'Utilidad neta', value: r.utilidad_neta, prev: a?.utilidad_neta, kind: 'final', sub: `margen neto ${pct(r.margen_neto_pct)}` },
  ];
  const fuera = r.fuera_del_resultado;
  const filasFuera: { label: string; value: number; nota: string }[] = [
    { label: 'Compras de mercancía del período', value: fuera.compras_mercancia, nota: 'van al inventario; se vuelven costo cuando se venden' },
    { label: 'Inversiones (activos)', value: fuera.inversiones, nota: 'no son gasto del mes' },
    { label: 'Abonos a crédito', value: fuera.abonos_credito, nota: 'capital de deuda, sale de caja' },
    { label: 'Envíos cobrados al cliente', value: fuera.envios_cobrados, nota: 'se cruzan con el registro de envíos' },
    { label: 'Compras registradas como gasto', value: fuera.compras_como_gasto, nota: 'registros viejos; ya están en el costo' },
  ].filter((x) => x.value > 0);

  return (
    <Card className="p-6">
      <div className="flex items-start justify-between flex-wrap gap-2 mb-4">
        <div>
          <h2 className="text-base font-bold flex items-center gap-2">
            <Scale className="w-5 h-5 text-brand-500" /> {titulo}
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Del {fechaCorta(r.periodo.desde)} al {fechaCorta(r.periodo.hasta)} · {r.periodo.dias} días, {r.periodo.dias_con_venta} con ventas
          </p>
        </div>
        {anterior && (
          <p className="text-xs text-muted-foreground">
            Comparado con {fechaCorta(anterior.periodo.desde)} → {fechaCorta(anterior.periodo.hasta)}
          </p>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full max-w-3xl">
          <thead>
            <tr className="text-[11px] uppercase tracking-wide text-muted-foreground">
              <th className="text-left font-semibold pb-2">Concepto</th>
              <th className="text-right font-semibold pb-2">Período</th>
              <th className="text-right font-semibold pb-2 pl-3">% ventas</th>
              {mostrarAnterior && <th className="text-right font-semibold pb-2 pl-3">Anterior</th>}
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => <FilaEstado key={f.label} f={f} ventas={r.ventas_netas} mostrarAnterior={mostrarAnterior} />)}
            <tr className="border-t border-dashed border-gray-200">
              <td className="py-2.5 pl-4 text-sm">
                <button type="button" onClick={() => setVerGastos((v) => !v)} className="inline-flex items-center gap-1 hover:text-brand-600">
                  <span className="text-rose-400">(−)</span> Gastos operativos
                  {verGastos ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />}
                </button>
                <span className="ml-2 text-xs text-muted-foreground">
                  fijos {money(r.gastos_fijos)} · variables {money(r.gastos_variables)}
                </span>
              </td>
              <td className="py-2.5 text-right tabular-nums text-sm text-rose-600 whitespace-nowrap">− {money(r.gastos_operativos)}</td>
              <td className="py-2.5 pl-3 text-right text-xs text-muted-foreground tabular-nums">{r.ventas_netas > 0 ? pct((r.gastos_operativos / r.ventas_netas) * 100) : ''}</td>
              {mostrarAnterior && <td className="py-2.5 pl-3 text-right text-xs tabular-nums text-muted-foreground">{money(a!.gastos_operativos)}</td>}
            </tr>
            {verGastos && filasGastos.map((f) => <FilaEstado key={f.label} f={f} ventas={r.ventas_netas} mostrarAnterior={mostrarAnterior} />)}
            {filasFinal.map((f) => <FilaEstado key={f.label} f={f} ventas={r.ventas_netas} mostrarAnterior={mostrarAnterior} />)}
          </tbody>
        </table>
      </div>

      {filasFuera.length > 0 && (
        <div className="mt-5 rounded-xl border border-dashed border-gray-300 bg-muted/20 p-4 max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Fuera del resultado (no son gasto del período)</p>
          <div className="space-y-1.5">
            {filasFuera.map((x) => (
              <div key={x.label} className="flex items-baseline justify-between gap-3 text-sm">
                <span>{x.label} <span className="text-xs text-muted-foreground">· {x.nota}</span></span>
                <span className="tabular-nums font-medium whitespace-nowrap">{money(x.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

// ─── Balance ────────────────────────────────────────────────────────────────

function Linea({ label, value, sub, strong, muted }: { label: string; value: string; sub?: string; strong?: boolean; muted?: boolean }) {
  return (
    <div className={`flex items-baseline justify-between gap-3 py-1.5 ${strong ? 'border-t-2 border-gray-300 mt-1 pt-2 font-bold' : 'border-t border-dashed border-gray-200'}`}>
      <span className={`text-sm ${muted ? 'text-muted-foreground' : ''}`}>
        {label}{sub && <span className="ml-1.5 text-xs font-normal text-muted-foreground">{sub}</span>}
      </span>
      <span className={`tabular-nums text-sm whitespace-nowrap ${muted ? 'text-muted-foreground' : ''}`}>{value}</span>
    </div>
  );
}

export function BalanceCard({ b }: { b: EstadosFinancieros['balance'] }) {
  const a = b.activos;
  const p = b.pasivos;
  return (
    <Card className="p-6">
      <h2 className="text-base font-bold flex items-center gap-2">
        <Banknote className="w-5 h-5 text-brand-500" /> Balance a hoy
      </h2>
      <p className="text-xs text-muted-foreground mt-0.5 mb-4">Lo que la tienda tiene y debe al {fechaCorta(b.fecha)}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-emerald-700 mb-1">Activos</p>
          <Linea label="Efectivo en caja" value={a.caja === null ? 'sin cierre' : money(a.caja)} sub={a.caja_fecha ? `cierre del ${fechaCorta(a.caja_fecha)}` : undefined} muted={a.caja === null} />
          <Linea label="Bold por consignar" value={money(a.bold_por_recibir)} sub="tarjeta de los últimos días, neto" />
          <Linea label="Cuentas por cobrar" value={money(a.cuentas_por_cobrar)} sub={`${a.ventas_por_cobrar} ventas con saldo`} />
          <Linea label="Inventario al costo" value={money(a.inventario_costo)} sub={`${a.inventario_unidades.toLocaleString('es-CO')} unidades · a precio de venta ${money(a.inventario_venta)}`} />
          <Linea label="Total activos" value={money(b.total_activos)} strong />
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-rose-700 mb-1">Pasivos</p>
          <Linea label="Proveedores por pagar" value={money(p.proveedores_por_pagar)} sub={`${p.facturas_por_pagar} facturas${p.proveedores_vencido > 0 ? ` · ${money(p.proveedores_vencido)} vencido` : ''}`} />
          <Linea label="Prestaciones provisionadas" value={money(p.prestaciones_provisionadas)} sub="cesantías, prima, vacaciones" />
          <Linea label="Total pasivos" value={money(b.total_pasivos)} strong />
          <div className="mt-4 rounded-xl bg-emerald-50 border border-emerald-200 p-3 flex items-baseline justify-between">
            <span className="text-sm font-semibold text-emerald-800">Capital de trabajo</span>
            <span className="text-lg font-bold tabular-nums text-emerald-700">{money(b.capital_trabajo)}</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

// ─── Flujo de caja ───────────────────────────────────────────────────────────

export function FlujoCajaCard({ f }: { f: EstadosFinancieros['flujo_caja'] }) {
  return (
    <Card className="p-6">
      <h2 className="text-base font-bold flex items-center gap-2">
        <CalendarRange className="w-5 h-5 text-brand-500" /> Flujo de caja del período
      </h2>
      <p className="text-xs text-muted-foreground mt-0.5 mb-4">Plata que entró y salió, por dónde. Cuenta cuando se cobra o se paga, no cuando se vende.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-emerald-700 mb-1">Entradas</p>
          {f.entradas.map((e) => <Linea key={e.metodo} label={e.metodo} value={money(e.total)} sub={`${e.n} cobros`} />)}
          <Linea label="Total entradas" value={money(f.total_entradas)} strong />
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-rose-700 mb-1">Salidas</p>
          {f.pagos_proveedores.map((e) => <Linea key={e.metodo} label={`Proveedores · ${e.metodo}`} value={money(e.total)} sub={`${e.n} facturas`} />)}
          <Linea label="Gastos operativos" value={money(f.gastos_operativos)} />
          {f.inversiones > 0 && <Linea label="Inversiones" value={money(f.inversiones)} />}
          {f.abonos_credito > 0 && <Linea label="Abonos a crédito" value={money(f.abonos_credito)} />}
          {f.compras_como_gasto > 0 && <Linea label="Compras registradas como gasto" value={money(f.compras_como_gasto)} />}
          <Linea label="Total salidas" value={money(f.total_salidas)} strong />
          <div className={`mt-4 rounded-xl border p-3 flex items-baseline justify-between ${f.flujo_neto >= 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'}`}>
            <span className="text-sm font-semibold">Flujo neto</span>
            <span className={`text-lg font-bold tabular-nums ${tono(f.flujo_neto)}`}>{money(f.flujo_neto)}</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

// ─── Historial ───────────────────────────────────────────────────────────────

export function HistorialCard({ h }: { h: EstadosFinancieros['historial'] }) {
  const data = h.map((m) => ({ ...m, mesLabel: mesCorto(m.mes) + (m.en_curso ? ' *' : '') }));
  return (
    <Card className="p-6">
      <h2 className="text-base font-bold flex items-center gap-2">
        <Gauge className="w-5 h-5 text-brand-500" /> Evolución mensual
      </h2>
      <p className="text-xs text-muted-foreground mt-0.5 mb-4">Últimos 6 meses calendario con las mismas reglas. * = mes en curso, incompleto.</p>
      <div className="h-64 mb-4">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data}>
            <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
            <XAxis dataKey="mesLabel" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="l" tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v / 1_000_000).toFixed(0)}M`} />
            <YAxis yAxisId="r" orientation="right" tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} domain={[0, 40]} />
            <Tooltip formatter={(v: number, name: string) => [name.includes('%') ? pct(v) : money(v), name]} />
            <Legend />
            <Bar yAxisId="l" dataKey="ventas_netas" name="Ventas netas" fill="#FF6B35" opacity={0.85} radius={[4, 4, 0, 0]} />
            <Bar yAxisId="l" dataKey="utilidad_bruta" name="Utilidad bruta" fill="#10b981" radius={[4, 4, 0, 0]} />
            <Bar yAxisId="l" dataKey="utilidad_neta" name="Utilidad neta" fill="#0f766e" radius={[4, 4, 0, 0]} />
            <Line yAxisId="r" type="monotone" dataKey="margen_bruto_pct" name="Margen bruto %" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] uppercase tracking-wide text-muted-foreground border-b">
              <th className="text-left py-1.5 font-semibold">Mes</th>
              <th className="text-right py-1.5 font-semibold">Ventas</th>
              <th className="text-right py-1.5 font-semibold">Costo</th>
              <th className="text-right py-1.5 font-semibold">Bruta</th>
              <th className="text-right py-1.5 font-semibold">Margen</th>
              <th className="text-right py-1.5 font-semibold">Gastos</th>
              <th className="text-right py-1.5 font-semibold">Neta</th>
              <th className="text-right py-1.5 font-semibold">Neto %</th>
            </tr>
          </thead>
          <tbody>
            {h.map((m) => (
              <tr key={m.mes} className={`border-b border-dashed border-gray-200 ${m.en_curso ? 'bg-amber-50/50' : ''}`}>
                <td className="py-1.5 font-medium">{mesCorto(m.mes)}{m.en_curso && <span className="text-xs text-muted-foreground"> · {m.dias} días</span>}</td>
                <td className="py-1.5 text-right tabular-nums">{money(m.ventas_netas)}</td>
                <td className="py-1.5 text-right tabular-nums text-muted-foreground">{money(m.costo_ventas)}</td>
                <td className="py-1.5 text-right tabular-nums">{money(m.utilidad_bruta)}</td>
                <td className="py-1.5 text-right tabular-nums text-muted-foreground">{pct(m.margen_bruto_pct)}</td>
                <td className="py-1.5 text-right tabular-nums text-rose-600">{money(m.gastos_operativos + m.comision_tarjeta)}</td>
                <td className={`py-1.5 text-right tabular-nums font-semibold ${tono(m.utilidad_neta)}`}>{money(m.utilidad_neta)}</td>
                <td className={`py-1.5 text-right tabular-nums ${tono(m.utilidad_neta)}`}>{pct(m.margen_neto_pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ─── Indicadores ─────────────────────────────────────────────────────────────

export function IndicadoresCard({ data }: { data: EstadosFinancieros }) {
  const i = data.indicadores;
  const r = data.resultados;
  const cobertura = Math.min(i.cobertura_pct, 150);
  const items: { label: string; value: string; sub?: string }[] = [
    { label: 'Ventas por día abierto', value: money(i.ventas_por_dia), sub: `${r.periodo.dias_con_venta} días con ventas` },
    { label: 'Ticket promedio', value: money(i.ticket_promedio), sub: `${i.unidades_por_venta} unidades por venta` },
    { label: 'Días de inventario', value: i.dias_de_inventario === null ? '—' : `${i.dias_de_inventario} días`, sub: i.rotacion_mensual === null ? undefined : `rota ${i.rotacion_mensual} veces al mes` },
    { label: 'Gastos sobre ventas', value: pct(i.gastos_sobre_ventas_pct), sub: `margen bruto ${pct(r.margen_bruto_pct)}` },
  ];
  return (
    <Card className="p-6">
      <h2 className="text-base font-bold mb-4">Indicadores</h2>
      <div className="grid grid-cols-2 gap-3 mb-5">
        {items.map((x) => (
          <div key={x.label} className="rounded-xl border bg-white p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{x.label}</p>
            <p className="text-lg font-bold tabular-nums">{x.value}</p>
            {x.sub && <p className="text-xs text-muted-foreground">{x.sub}</p>}
          </div>
        ))}
      </div>
      <div className="rounded-xl border p-4">
        <div className="flex items-baseline justify-between mb-1">
          <p className="text-sm font-semibold">Punto de equilibrio del período</p>
          <p className="text-sm tabular-nums">{money(i.punto_equilibrio)}</p>
        </div>
        <p className="text-xs text-muted-foreground mb-2">
          Lo que había que vender, con el margen real, para pagar los gastos del período. Se vendió el {pct(i.cobertura_pct)}.
        </p>
        <div className="h-3 rounded-full bg-gray-100 overflow-hidden relative">
          <div className={`h-full rounded-full ${i.cobertura_pct >= 100 ? 'bg-emerald-500' : 'bg-rose-500'}`} style={{ width: `${(cobertura / 150) * 100}%` }} />
          <div className="absolute top-0 bottom-0 w-0.5 bg-gray-700" style={{ left: `${(100 / 150) * 100}%` }} title="100 % = equilibrio" />
        </div>
      </div>
    </Card>
  );
}

// ─── Alertas y supuestos ─────────────────────────────────────────────────────

const ICONO = { info: Info, warning: AlertTriangle, danger: OctagonAlert } as const;
const TONO = { info: 'border-blue-200 bg-blue-50 text-blue-800', warning: 'border-amber-200 bg-amber-50 text-amber-800', danger: 'border-rose-200 bg-rose-50 text-rose-800' } as const;

export function AlertasCard({ data }: { data: EstadosFinancieros }) {
  const [verSupuestos, setVerSupuestos] = useState(false);
  return (
    <Card className="p-6">
      <h2 className="text-base font-bold mb-3">Calidad del dato</h2>
      {data.alertas.length === 0 ? (
        <p className="text-sm text-emerald-700">Sin reparos: todas las líneas tienen costo y los gastos están clasificados.</p>
      ) : (
        <div className="space-y-2">
          {data.alertas.map((al, idx) => {
            const Icon = ICONO[al.nivel];
            return (
              <div key={idx} className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-sm ${TONO[al.nivel]}`}>
                <Icon className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{al.texto}</span>
              </div>
            );
          })}
        </div>
      )}
      <button type="button" onClick={() => setVerSupuestos((v) => !v)} className="mt-4 text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
        {verSupuestos ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />} Cómo se calcula
      </button>
      {verSupuestos && (
        <ul className="mt-2 space-y-1 text-xs text-muted-foreground list-disc pl-5">
          {data.supuestos.map((s, idx) => <li key={idx}>{s}</li>)}
        </ul>
      )}
    </Card>
  );
}

export function EstadoBadge({ r }: { r: EstadoResultados }) {
  if (r.utilidad_neta < 0) return <Badge variant="danger">En pérdida</Badge>;
  if (r.cobertura_pct < 110) return <Badge variant="warning">Ajustado</Badge>;
  return <Badge variant="success">Sano</Badge>;
}
