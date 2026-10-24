'use client';

/**
 * Nómina quincenal (15-oct-2026).
 *
 * Diego: *"yo veo el valor de la liquidación, o sea cuánto debo pagarle, y le
 * consigno al empleado; pero el admin registra el pago cuando yo le dé al botón"*.
 *
 * La pantalla gira alrededor de UN número: el neto de la quincena pendiente. El
 * botón "Pagar nómina de la quincena" congela esa liquidación, crea los dos gastos
 * (neto consignado + provisión de prestaciones), manda el desprendible en PDF al
 * correo del empleado y deja el registro en el historial. Nada más que apretar.
 */

import { useMemo, useState } from 'react';
import { useBorrador, descartarBorrador } from '@/lib/borradores';
import { BorradorAviso } from '@/components/BorradorAviso';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle, BadgeDollarSign, CheckCircle2, Download, FileText, Loader2, Mail,
  Pencil, PiggyBank, Plus, RefreshCw, Send, User, XCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  nomina, type NominaEmpleado, type NominaEmpleadoIn, type NominaLiquidacion, type NominaPago,
  type NominaParametro, type NominaResumen,
} from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';

const METODOS = ['Transferencia', 'Bancolombia', 'Nequi', 'Daviplata', 'Efectivo'];

function fechaCorta(iso: string | null | undefined) {
  if (!iso) return '—';
  const [y, m, d] = iso.slice(0, 10).split('-');
  return `${d}/${m}/${y}`;
}

function descargar(blob: Blob, nombre: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nombre;
  a.click();
  URL.revokeObjectURL(url);
}

export default function NominaPage() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ['nomina'], queryFn: nomina.resumen });
  const [empleadoId, setEmpleadoId] = useBorrador<string | null>('vista:nomina:empleado', null);
  const [editando, setEditando] = useBorrador<NominaEmpleado | null | 'nuevo'>('nomina:editando', null);
  const [editParam, setEditParam] = useState(false);

  const activos = useMemo(() => data?.empleados.filter((e) => e.activo) ?? [], [data]);
  const empleado = useMemo(
    () => data?.empleados.find((e) => e.id === empleadoId) ?? activos[0] ?? data?.empleados[0] ?? null,
    [data, activos, empleadoId],
  );

  const refrescar = () => qc.invalidateQueries({ queryKey: ['nomina'] });

  if (isLoading) {
    return <div className="flex items-center gap-2 text-muted-foreground py-16 justify-center"><Loader2 className="w-5 h-5 animate-spin" /> Cargando nómina…</div>;
  }
  if (error || !data) {
    return <Card className="p-6 text-red-600 flex items-center gap-2"><AlertTriangle className="w-5 h-5" /> No se pudo cargar la nómina: {(error as Error)?.message}</Card>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <BadgeDollarSign className="w-6 h-6 text-brand-600" /> Nómina
          </h1>
          <p className="text-sm text-muted-foreground">
            Liquidación quincenal con salario mínimo, auxilio de transporte y descuentos de ley. El pago queda registrado en Gastos y el desprendible llega al correo del empleado.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {data.empleados.length > 1 && (
            <Select value={empleado?.id ?? ''} onChange={(e) => setEmpleadoId(e.target.value)}>
              {data.empleados.map((e) => <option key={e.id} value={e.id}>{e.nombre}{e.activo ? '' : ' (inactivo)'}</option>)}
            </Select>
          )}
          <Button variant="outline" onClick={() => setEditando('nuevo')}><Plus className="w-4 h-4" /> Empleado</Button>
        </div>
      </div>

      {!empleado ? (
        <Card className="p-8 text-center text-muted-foreground">No hay empleados registrados todavía.</Card>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <div className="xl:col-span-2 space-y-4">
            <LiquidacionCard empleado={empleado} onPagado={refrescar} />
          </div>
          <div className="space-y-4">
            <EmpleadoCard empleado={empleado} onEditar={() => setEditando(empleado)} onCambio={refrescar} />
            <ProvisionCard empleado={empleado} />
            <ParametrosCard param={data.parametros_vigentes} onEditar={() => setEditParam(true)} />
          </div>
        </div>
      )}

      <Historial pagos={data.historial} onCambio={refrescar} />

      <Dialog open={editando !== null} onClose={() => setEditando(null)} title={editando === 'nuevo' ? 'Nuevo empleado' : 'Editar empleado'} size="md">
        {editando !== null && (
          <EmpleadoForm
            inicial={editando === 'nuevo' ? null : editando}
            minimo={data.parametros_vigentes}
            onListo={() => { setEditando(null); refrescar(); }}
          />
        )}
      </Dialog>

      <Dialog open={editParam} onClose={() => setEditParam(false)} title="Salario mínimo y auxilio" size="md">
        {editParam && <ParametroForm actual={data.parametros_vigentes} onListo={() => { setEditParam(false); refrescar(); }} />}
      </Dialog>
    </div>
  );
}

// ───────────────────────── Liquidación de la quincena ─────────────────────────

function LiquidacionCard({ empleado, onPagado }: { empleado: NominaEmpleado; onPagado: () => void }) {
  const pend = empleado.pendiente;
  // la clave lleva la quincena: una quincena nueva arranca limpia sola, y la que
  // está a medio liquidar sobrevive a salir de Nómina (lib/borradores.ts)
  const clave = `nomina:liq:${empleado.id}:${pend?.periodo.clave ?? 'sin'}`;
  const [dias, setDias] = useBorrador(`${clave}:dias`, pend?.dias_sugeridos ?? 15);
  const [otrosDev, setOtrosDev] = useBorrador(`${clave}:otrosDev`, 0);
  const [otrosDesc, setOtrosDesc] = useBorrador(`${clave}:otrosDesc`, 0);
  const [descOtros, setDescOtros] = useBorrador(`${clave}:descOtros`, '');
  const [metodo, setMetodo] = useBorrador(`${clave}:metodo`, 'Transferencia');
  const [enviarCorreo, setEnviarCorreo] = useBorrador(`${clave}:correo`, true);
  const [confirmar, setConfirmar] = useState(false);
  const [ultimo, setUltimo] = useState<NominaPago | null>(null);

  const ajustado = dias !== (pend?.dias_sugeridos ?? 15) || otrosDev > 0 || otrosDesc > 0;
  const preview = useQuery({
    queryKey: ['nomina-liq', empleado.id, dias, otrosDev, otrosDesc],
    queryFn: () => nomina.liquidacion({ employee_id: empleado.id, dias, otros_devengados: otrosDev, otros_descuentos: otrosDesc }),
    enabled: !!pend && ajustado,
  });
  const liq: NominaLiquidacion | undefined = ajustado ? preview.data?.liquidacion : pend?.liquidacion;

  const pagar = useMutation({
    mutationFn: () => nomina.pagar({
      employee_id: empleado.id,
      periodo_clave: pend!.periodo.clave,
      dias_trabajados: dias,
      otros_devengados: otrosDev,
      otros_descuentos: otrosDesc,
      descripcion_otros: descOtros || null,
      metodo_pago: metodo,
      banco_origen: null,
      fecha_pago: null,
      enviar_correo: enviarCorreo,
    }),
    onSuccess: (p) => {
      setConfirmar(false);
      setUltimo(p);
      descartarBorrador(clave);
      if (p.email_enviado_at) toast.success(`Quincena pagada y desprendible enviado a ${p.email_enviado_a}`);
      else if (enviarCorreo) toast.warning(`Quincena pagada, pero el correo falló: ${p.email_error ?? 'sin detalle'}. Puedes reenviarlo desde el historial.`);
      else toast.success('Quincena pagada y registrada en Gastos');
      onPagado();
    },
    onError: (e: Error) => toast.error(e.message || 'No se pudo registrar el pago'),
  });

  if (!pend) {
    return (
      <Card className="p-6">
        <div className="text-sm text-muted-foreground">{empleado.nombre} está inactivo: no hay quincena por liquidar.</div>
        {ultimo && <UltimoPago pago={ultimo} />}
      </Card>
    );
  }

  return (
    <Card className="p-5 space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-xs uppercase tracking-wider text-muted-foreground">Quincena pendiente</div>
          <div className="text-lg font-bold">{pend.periodo.etiqueta}</div>
          <div className="text-xs text-muted-foreground">
            {pend.quincena_terminada ? 'La quincena ya terminó.' : 'La quincena todavía está en curso.'} {empleado.nombre} · {empleado.cargo}
          </div>
        </div>
        <Badge variant={pend.puede_pagar ? 'warning' : 'neutral'}>{pend.puede_pagar ? 'Por pagar' : 'No disponible'}</Badge>
      </div>

      {/* Ajustes */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <label className="text-xs font-medium mb-1 block">Días trabajados</label>
          <Input type="number" min={0} max={15} value={dias} onChange={(e) => setDias(Math.max(0, Math.min(15, parseInt(e.target.value) || 0)))} />
        </div>
        <div>
          <label className="text-xs font-medium mb-1 block">Otros devengados</label>
          <Input type="number" min={0} step={1000} value={otrosDev || ''} placeholder="0" onChange={(e) => setOtrosDev(Math.max(0, parseFloat(e.target.value) || 0))} />
        </div>
        <div>
          <label className="text-xs font-medium mb-1 block">Anticipos / otros descuentos</label>
          <Input type="number" min={0} step={1000} value={otrosDesc || ''} placeholder="0" onChange={(e) => setOtrosDesc(Math.max(0, parseFloat(e.target.value) || 0))} />
        </div>
        <div>
          <label className="text-xs font-medium mb-1 block">Método de pago</label>
          <Select value={metodo} onChange={(e) => setMetodo(e.target.value)}>
            {METODOS.map((m) => <option key={m} value={m}>{m}</option>)}
          </Select>
        </div>
      </div>
      {otrosDesc > 0 && (
        <Input value={descOtros} onChange={(e) => setDescOtros(e.target.value)} placeholder="Concepto del descuento (sale en el desprendible), p. ej. Anticipo del 3 de octubre" />
      )}

      {/* Liquidación */}
      {!liq ? (
        <div className="text-sm text-muted-foreground flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Calculando…</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <TablaLiq
            titulo="Devengado"
            filas={[
              [`Salario básico (${liq.dias_trabajados} días)`, liq.dev_salario],
              ['Auxilio de transporte', liq.dev_auxilio],
              ...(liq.otros_devengados > 0 ? [['Otros devengados', liq.otros_devengados] as [string, number]] : []),
            ]}
            total={['Total devengado', liq.total_devengado]}
          />
          <TablaLiq
            titulo="Deducciones"
            filas={[
              [`Salud ${liq.pct_salud}%`, liq.ded_salud],
              [`Pensión ${liq.pct_pension}%`, liq.ded_pension],
              ...(liq.otros_descuentos > 0 ? [[descOtros || 'Otros descuentos', liq.otros_descuentos] as [string, number]] : []),
            ]}
            total={['Total deducciones', liq.total_deducciones]}
          />
        </div>
      )}

      {liq && (
        <div className="rounded-xl border-2 border-brand-600/60 bg-brand-500/5 p-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs uppercase tracking-wider text-brand-700 font-semibold">Neto a consignar</div>
            <div className="text-3xl font-black text-brand-700">{formatCurrency(liq.neto)}</div>
            <div className="text-xs text-muted-foreground mt-1">
              Además se registra una provisión de prestaciones de {formatCurrency(liq.total_provision)} por esta quincena.
            </div>
            {liq.notas.map((n) => <div key={n} className="text-xs text-amber-700 mt-1 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> {n}</div>)}
          </div>
          <div className="flex flex-col items-end gap-2">
            <label className="text-xs flex items-center gap-2 text-muted-foreground">
              <input type="checkbox" checked={enviarCorreo} onChange={(e) => setEnviarCorreo(e.target.checked)} />
              Enviar desprendible a {empleado.email || 'sin correo'}
            </label>
            <Button size="lg" disabled={!pend.puede_pagar || pagar.isPending || liq.neto <= 0} onClick={() => setConfirmar(true)}>
              <CheckCircle2 className="w-5 h-5" /> Pagar nómina de la quincena
            </Button>
            {!pend.puede_pagar && pend.motivo && <div className="text-xs text-muted-foreground">{pend.motivo}</div>}
          </div>
        </div>
      )}

      {ultimo && <UltimoPago pago={ultimo} />}

      <Dialog open={confirmar} onClose={() => !pagar.isPending && setConfirmar(false)} title="Confirmar pago de nómina" size="sm">
        <DialogBody className="space-y-3 text-sm">
          <p>Vas a registrar el pago de la quincena del <strong>{pend.periodo.etiqueta}</strong> a <strong>{empleado.nombre}</strong>.</p>
          <div className="rounded-lg bg-muted p-3 space-y-1">
            <div className="flex justify-between"><span>Neto consignado por {metodo}</span><strong>{formatCurrency(liq?.neto ?? 0)}</strong></div>
            <div className="flex justify-between text-muted-foreground"><span>Provisión prestaciones (gasto aparte)</span><span>{formatCurrency(liq?.total_provision ?? 0)}</span></div>
          </div>
          <p className="text-muted-foreground">Se crean los dos gastos en Gastos{enviarCorreo ? ' y se envía el desprendible en PDF al correo del empleado con copia a la tienda' : ''}. Esta quincena no se podrá pagar dos veces.</p>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setConfirmar(false)} disabled={pagar.isPending}>Cancelar</Button>
          <Button onClick={() => pagar.mutate()} disabled={pagar.isPending}>
            {pagar.isPending ? <><Loader2 className="w-4 h-4 animate-spin" /> Registrando…</> : 'Sí, ya le consigné: registrar pago'}
          </Button>
        </DialogFooter>
      </Dialog>
    </Card>
  );
}

function TablaLiq({ titulo, filas, total }: { titulo: string; filas: [string, number][]; total: [string, number] }) {
  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <div className="px-3 py-2 bg-muted/50 text-xs uppercase tracking-wider text-muted-foreground">{titulo}</div>
      <table className="w-full text-sm">
        <tbody>
          {filas.map(([k, v]) => (
            <tr key={k} className="border-t border-border"><td className="px-3 py-2">{k}</td><td className="px-3 py-2 text-right tabular-nums">{formatCurrency(v)}</td></tr>
          ))}
          <tr className="border-t-2 border-border font-bold bg-muted/30"><td className="px-3 py-2">{total[0]}</td><td className="px-3 py-2 text-right tabular-nums">{formatCurrency(total[1])}</td></tr>
        </tbody>
      </table>
    </div>
  );
}

function UltimoPago({ pago }: { pago: NominaPago }) {
  return (
    <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/5 p-3 text-sm flex flex-wrap items-center justify-between gap-2">
      <div className="flex items-center gap-2">
        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
        Pago N.º {String(pago.consecutivo).padStart(5, '0')} registrado: {formatCurrency(pago.neto)} · {pago.periodo.etiqueta}
        {pago.email_enviado_at ? <Badge variant="success">Correo enviado</Badge> : <Badge variant="danger">Correo no enviado</Badge>}
      </div>
      <BotonPdf pagoId={pago.id} consecutivo={pago.consecutivo} />
    </div>
  );
}

function BotonPdf({ pagoId, consecutivo }: { pagoId: string; consecutivo: number }) {
  const [cargando, setCargando] = useState(false);
  return (
    <Button variant="outline" size="sm" disabled={cargando} onClick={async () => {
      setCargando(true);
      try { descargar(await nomina.desprendiblePdf(pagoId), `desprendible-${String(consecutivo).padStart(5, '0')}.pdf`); }
      catch (e) { toast.error((e as Error).message); }
      finally { setCargando(false); }
    }}>
      {cargando ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />} PDF
    </Button>
  );
}

// ───────────────────────── Empleado ─────────────────────────

function EmpleadoCard({ empleado, onEditar, onCambio }: { empleado: NominaEmpleado; onEditar: () => void; onCambio: () => void }) {
  const [bajando, setBajando] = useState(false);
  const [confirmarEnvio, setConfirmarEnvio] = useState(false);
  const enviar = useMutation({
    mutationFn: () => nomina.enviarContrato(empleado.id),
    onSuccess: (e) => { toast.success(`Contrato enviado a ${e.contrato_enviado_a}`); setConfirmarEnvio(false); onCambio(); },
    onError: (e: Error) => toast.error(e.message || 'No se pudo enviar el contrato'),
  });
  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-full bg-brand-500/15 text-brand-700 flex items-center justify-center"><User className="w-4 h-4" /></div>
          <div>
            <div className="font-bold leading-tight">{empleado.nombre}</div>
            <div className="text-xs text-muted-foreground">{empleado.cargo} · C.C. {empleado.documento}</div>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={onEditar}><Pencil className="w-3.5 h-3.5" /></Button>
      </div>
      <dl className="text-sm grid grid-cols-2 gap-x-3 gap-y-1">
        <dt className="text-muted-foreground">Ingreso</dt><dd>{fechaCorta(empleado.fecha_ingreso)}</dd>
        <dt className="text-muted-foreground">Contrato</dt><dd className="capitalize">{empleado.tipo_contrato}</dd>
        <dt className="text-muted-foreground">Salario</dt><dd>{formatCurrency(empleado.salario_base)} {empleado.usa_minimo && <span className="text-xs text-muted-foreground">(mínimo)</span>}</dd>
        <dt className="text-muted-foreground">Auxilio</dt><dd>{formatCurrency(empleado.aux_transporte)}</dd>
        <dt className="text-muted-foreground">Correo</dt><dd className="truncate">{empleado.email || '—'}</dd>
        <dt className="text-muted-foreground">Quincenas</dt><dd>{empleado.acumulado.quincenas_pagadas} pagadas · {formatCurrency(empleado.acumulado.neto_pagado)}</dd>
      </dl>
      <div className="pt-2 border-t border-border space-y-2">
        <div className="text-xs uppercase tracking-wider text-muted-foreground flex items-center gap-1"><FileText className="w-3.5 h-3.5" /> Contrato de trabajo</div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" disabled={bajando} onClick={async () => {
            setBajando(true);
            try { descargar(await nomina.contratoPdf(empleado.id), `contrato-${empleado.documento}.pdf`); }
            catch (e) { toast.error((e as Error).message); }
            finally { setBajando(false); }
          }}>
            {bajando ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />} Ver PDF
          </Button>
          <Button variant="outline" size="sm" disabled={!empleado.email || enviar.isPending} onClick={() => setConfirmarEnvio(true)}>
            <Send className="w-3.5 h-3.5" /> Enviar al correo
          </Button>
        </div>
        {empleado.contrato_enviado_at
          ? <div className="text-xs text-emerald-700 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Enviado a {empleado.contrato_enviado_a} el {fechaCorta(empleado.contrato_enviado_at)}</div>
          : <div className="text-xs text-muted-foreground">Todavía no se ha enviado por correo.</div>}
      </div>

      <Dialog open={confirmarEnvio} onClose={() => setConfirmarEnvio(false)} title="Enviar contrato" size="sm">
        <DialogBody className="text-sm space-y-2">
          <p>Se envía el contrato en PDF a <strong>{empleado.email}</strong> con copia al correo de la tienda, para dejar constancia.</p>
          <p className="text-muted-foreground">Revisa primero el PDF con "Ver PDF" si no lo has leído.</p>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setConfirmarEnvio(false)}>Cancelar</Button>
          <Button onClick={() => enviar.mutate()} disabled={enviar.isPending}>{enviar.isPending ? 'Enviando…' : 'Enviar'}</Button>
        </DialogFooter>
      </Dialog>
    </Card>
  );
}

function EmpleadoForm({ inicial, minimo, onListo }: { inicial: NominaEmpleado | null; minimo: NominaParametro; onListo: () => void }) {
  const claveForm = `nomina:empleado:${inicial?.id ?? 'nuevo'}`;
  const [f, setF] = useBorrador<NominaEmpleadoIn>(claveForm, {
    nombre: inicial?.nombre ?? '',
    documento: inicial?.documento ?? '',
    email: inicial?.email ?? '',
    cargo: inicial?.cargo ?? 'Auxiliar',
    fecha_ingreso: inicial?.fecha_ingreso ?? new Date().toISOString().slice(0, 10),
    fecha_retiro: inicial?.fecha_retiro ?? null,
    salario_base: inicial && !inicial.usa_minimo ? inicial.salario_base : null,
    aux_transporte: inicial && !inicial.usa_minimo ? inicial.aux_transporte : null,
    tipo_contrato: inicial?.tipo_contrato ?? 'indefinido',
    activo: inicial?.activo ?? true,
    notas: inicial?.notas ?? '',
  });
  const usaMinimo = f.salario_base === null;
  const guardar = useMutation({
    mutationFn: () => (inicial ? nomina.editarEmpleado(inicial.id, f) : nomina.crearEmpleado(f)),
    onSuccess: () => { toast.success('Empleado guardado'); descartarBorrador(claveForm); onListo(); },
    onError: (e: Error) => toast.error(e.message || 'No se pudo guardar'),
  });
  return (
    <form onSubmit={(e) => { e.preventDefault(); guardar.mutate(); }}>
      <DialogBody className="space-y-3">
        <BorradorAviso prefijo={claveForm} />
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><label className="text-xs font-medium mb-1 block">Nombre completo</label><Input value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} required /></div>
          <div><label className="text-xs font-medium mb-1 block">Cédula</label><Input value={f.documento} onChange={(e) => setF({ ...f, documento: e.target.value })} required /></div>
          <div><label className="text-xs font-medium mb-1 block">Cargo</label><Input value={f.cargo} onChange={(e) => setF({ ...f, cargo: e.target.value })} required /></div>
          <div className="col-span-2"><label className="text-xs font-medium mb-1 block">Correo (recibe el desprendible)</label><Input type="email" value={f.email ?? ''} onChange={(e) => setF({ ...f, email: e.target.value })} /></div>
          <div><label className="text-xs font-medium mb-1 block">Fecha de ingreso</label><Input type="date" value={f.fecha_ingreso} onChange={(e) => setF({ ...f, fecha_ingreso: e.target.value })} required /></div>
          <div><label className="text-xs font-medium mb-1 block">Fecha de retiro</label><Input type="date" value={f.fecha_retiro ?? ''} onChange={(e) => setF({ ...f, fecha_retiro: e.target.value || null })} /></div>
          <div><label className="text-xs font-medium mb-1 block">Tipo de contrato</label>
            <Select value={f.tipo_contrato} onChange={(e) => setF({ ...f, tipo_contrato: e.target.value })}>
              <option value="indefinido">Término indefinido</option>
              <option value="fijo">Término fijo</option>
              <option value="obra o labor">Obra o labor</option>
            </Select>
          </div>
          <div className="flex items-end gap-2 pb-2">
            <label className="text-sm flex items-center gap-2"><input type="checkbox" checked={f.activo} onChange={(e) => setF({ ...f, activo: e.target.checked })} /> Activo</label>
          </div>
        </div>
        <label className="text-sm flex items-center gap-2">
          <input type="checkbox" checked={usaMinimo} onChange={(e) => setF({ ...f, salario_base: e.target.checked ? null : minimo.smmlv, aux_transporte: e.target.checked ? null : minimo.aux_transporte })} />
          Gana el salario mínimo vigente ({formatCurrency(minimo.smmlv)} + auxilio {formatCurrency(minimo.aux_transporte)})
        </label>
        {!usaMinimo && (
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs font-medium mb-1 block">Salario mensual</label><Input type="number" min={0} value={f.salario_base ?? ''} onChange={(e) => setF({ ...f, salario_base: parseFloat(e.target.value) || 0 })} /></div>
            <div><label className="text-xs font-medium mb-1 block">Auxilio mensual</label><Input type="number" min={0} value={f.aux_transporte ?? ''} onChange={(e) => setF({ ...f, aux_transporte: parseFloat(e.target.value) || 0 })} /></div>
          </div>
        )}
        <div><label className="text-xs font-medium mb-1 block">Notas</label><Input value={f.notas ?? ''} onChange={(e) => setF({ ...f, notas: e.target.value })} /></div>
      </DialogBody>
      <DialogFooter>
        <Button type="submit" disabled={guardar.isPending}>{guardar.isPending ? 'Guardando…' : 'Guardar'}</Button>
      </DialogFooter>
    </form>
  );
}

// ───────────────────────── Provisión y parámetros ─────────────────────────

function ProvisionCard({ empleado }: { empleado: NominaEmpleado }) {
  const m = empleado.provision_mensual;
  const a = empleado.acumulado.provision;
  const filas: [string, number, number, string][] = [
    ['Cesantías', m.cesantias, a.cesantias, 'se consignan al fondo antes del 14 de febrero'],
    ['Intereses cesantías', m.intereses_cesantias, a.intereses_cesantias, 'se pagan al empleado en enero'],
    ['Prima de servicios', m.prima, a.prima, 'se paga en junio y en diciembre'],
    ['Vacaciones', m.vacaciones, a.vacaciones, '15 días por cada año trabajado'],
  ];
  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-center gap-2">
        <PiggyBank className="w-4 h-4 text-brand-600" />
        <div className="font-bold">Provisión de prestaciones</div>
      </div>
      <div className="text-xs text-muted-foreground">
        Lo que vas debiendo por fuera del sueldo. Cada quincena pagada deja su parte registrada en Gastos como provisión, para que el punto de equilibrio lo tenga en cuenta.
      </div>
      <table className="w-full text-sm">
        <thead className="text-xs uppercase text-muted-foreground"><tr><th className="text-left py-1">Concepto</th><th className="text-right py-1">Mensual</th><th className="text-right py-1">Acumulado</th></tr></thead>
        <tbody>
          {filas.map(([k, mes, acum, nota]) => (
            <tr key={k} className="border-t border-border">
              <td className="py-1.5"><div>{k}</div><div className="text-[11px] text-muted-foreground">{nota}</div></td>
              <td className="py-1.5 text-right tabular-nums">{formatCurrency(mes)}</td>
              <td className="py-1.5 text-right tabular-nums font-medium">{formatCurrency(acum)}</td>
            </tr>
          ))}
          <tr className="border-t-2 border-border font-bold"><td className="py-1.5">Total</td><td className="py-1.5 text-right tabular-nums">{formatCurrency(m.total)}</td><td className="py-1.5 text-right tabular-nums">{formatCurrency(a.total)}</td></tr>
        </tbody>
      </table>
      <div className="text-[11px] text-muted-foreground">
        Cuando pagues la prima o consignes las cesantías, no las registres otra vez como gasto: ya están provisionadas aquí. La seguridad social del empleador (PILA) va aparte.
      </div>
    </Card>
  );
}

function ParametrosCard({ param, onEditar }: { param: NominaParametro; onEditar: () => void }) {
  return (
    <Card className="p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div className="font-bold text-sm">Valores legales vigentes</div>
        <Button variant="ghost" size="sm" onClick={onEditar}><Pencil className="w-3.5 h-3.5" /></Button>
      </div>
      <dl className="text-sm grid grid-cols-2 gap-x-3 gap-y-1">
        <dt className="text-muted-foreground">Salario mínimo</dt><dd className="text-right tabular-nums">{formatCurrency(param.smmlv)}</dd>
        <dt className="text-muted-foreground">Aux. transporte</dt><dd className="text-right tabular-nums">{formatCurrency(param.aux_transporte)}</dd>
        <dt className="text-muted-foreground">Salud / pensión</dt><dd className="text-right">{param.pct_salud}% / {param.pct_pension}%</dd>
        <dt className="text-muted-foreground">Vigente desde</dt><dd className="text-right">{fechaCorta(param.vigencia_desde)}</dd>
      </dl>
      {param.fuente && <div className="text-[11px] text-muted-foreground">{param.fuente}</div>}
    </Card>
  );
}

function ParametroForm({ actual, onListo }: { actual: NominaParametro; onListo: () => void }) {
  const anio = new Date().getFullYear() + 1;
  const [f, setF] = useState<NominaParametro>({ vigencia_desde: `${anio}-01-01`, smmlv: actual.smmlv, aux_transporte: actual.aux_transporte, pct_salud: actual.pct_salud, pct_pension: actual.pct_pension, fuente: '' });
  const guardar = useMutation({
    mutationFn: () => nomina.guardarParametro(f),
    onSuccess: () => { toast.success('Parámetros guardados'); onListo(); },
    onError: (e: Error) => toast.error(e.message || 'No se pudo guardar'),
  });
  return (
    <form onSubmit={(e) => { e.preventDefault(); guardar.mutate(); }}>
      <DialogBody className="space-y-3">
        <p className="text-sm text-muted-foreground">Registra el mínimo de una nueva vigencia (normalmente el 1 de enero). Las quincenas anteriores conservan el valor con el que se pagaron.</p>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="text-xs font-medium mb-1 block">Vigente desde</label><Input type="date" value={f.vigencia_desde} onChange={(e) => setF({ ...f, vigencia_desde: e.target.value })} required /></div>
          <div><label className="text-xs font-medium mb-1 block">Salario mínimo</label><Input type="number" min={0} value={f.smmlv} onChange={(e) => setF({ ...f, smmlv: parseFloat(e.target.value) || 0 })} required /></div>
          <div><label className="text-xs font-medium mb-1 block">Auxilio de transporte</label><Input type="number" min={0} value={f.aux_transporte} onChange={(e) => setF({ ...f, aux_transporte: parseFloat(e.target.value) || 0 })} required /></div>
          <div className="grid grid-cols-2 gap-2">
            <div><label className="text-xs font-medium mb-1 block">Salud %</label><Input type="number" min={0} max={100} step={0.5} value={f.pct_salud} onChange={(e) => setF({ ...f, pct_salud: parseFloat(e.target.value) || 0 })} /></div>
            <div><label className="text-xs font-medium mb-1 block">Pensión %</label><Input type="number" min={0} max={100} step={0.5} value={f.pct_pension} onChange={(e) => setF({ ...f, pct_pension: parseFloat(e.target.value) || 0 })} /></div>
          </div>
          <div className="col-span-2"><label className="text-xs font-medium mb-1 block">Fuente (decreto)</label><Input value={f.fuente ?? ''} onChange={(e) => setF({ ...f, fuente: e.target.value })} /></div>
        </div>
      </DialogBody>
      <DialogFooter><Button type="submit" disabled={guardar.isPending}>{guardar.isPending ? 'Guardando…' : 'Guardar'}</Button></DialogFooter>
    </form>
  );
}

// ───────────────────────── Historial ─────────────────────────

function Historial({ pagos, onCambio }: { pagos: NominaPago[]; onCambio: () => void }) {
  const reenviar = useMutation({
    mutationFn: (id: string) => nomina.reenviar(id),
    onSuccess: (p) => { toast.success(`Desprendible reenviado a ${p.email_enviado_a}`); onCambio(); },
    onError: (e: Error) => toast.error(e.message || 'No se pudo reenviar'),
  });
  return (
    <Card className="overflow-hidden">
      <div className="px-4 py-3 border-b border-border font-bold text-sm">Historial de quincenas pagadas</div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="text-left px-4 py-3">N.º</th>
              <th className="text-left px-4 py-3">Empleado</th>
              <th className="text-left px-4 py-3">Quincena</th>
              <th className="text-left px-4 py-3">Pagada</th>
              <th className="text-right px-4 py-3">Devengado</th>
              <th className="text-right px-4 py-3">Deducciones</th>
              <th className="text-right px-4 py-3">Neto</th>
              <th className="text-right px-4 py-3">Provisión</th>
              <th className="text-left px-4 py-3">Correo</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {pagos.length === 0 ? (
              <tr><td colSpan={10} className="text-center py-8 text-muted-foreground">Todavía no hay quincenas pagadas.</td></tr>
            ) : pagos.map((p) => (
              <tr key={p.id} className="border-t border-border hover:bg-muted/30">
                <td className="px-4 py-2 tabular-nums text-muted-foreground">{String(p.consecutivo).padStart(5, '0')}</td>
                <td className="px-4 py-2">{p.employee_nombre}</td>
                <td className="px-4 py-2">{p.periodo.etiqueta}<div className="text-[11px] text-muted-foreground">{p.dias_trabajados} días</div></td>
                <td className="px-4 py-2">{fechaCorta(p.fecha_pago)}<div className="text-[11px] text-muted-foreground">{p.metodo_pago}</div></td>
                <td className="px-4 py-2 text-right tabular-nums">{formatCurrency(p.total_devengado)}</td>
                <td className="px-4 py-2 text-right tabular-nums text-red-600">-{formatCurrency(p.total_deducciones)}</td>
                <td className="px-4 py-2 text-right tabular-nums font-bold">{formatCurrency(p.neto)}</td>
                <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">{formatCurrency(p.total_provision)}</td>
                <td className="px-4 py-2">
                  {p.email_enviado_at
                    ? <span className="inline-flex items-center gap-1 text-emerald-700 text-xs"><Mail className="w-3 h-3" /> {fechaCorta(p.email_enviado_at)}</span>
                    : <span className="inline-flex items-center gap-1 text-red-600 text-xs" title={p.email_error ?? ''}><XCircle className="w-3 h-3" /> No enviado</span>}
                </td>
                <td className="px-4 py-2 text-right whitespace-nowrap">
                  <div className="inline-flex gap-1">
                    <BotonPdf pagoId={p.id} consecutivo={p.consecutivo} />
                    <Button variant="outline" size="sm" disabled={reenviar.isPending} onClick={() => reenviar.mutate(p.id)} title="Reenviar desprendible al correo">
                      {reenviar.isPending && reenviar.variables === p.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
