'use client';

import { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShoppingCart, Upload, FileText, Plus, Trash2, Search, Save, Eye, Truck, Sparkles,
  AlertTriangle, CheckCircle2, Package, X, FileUp, Edit2, RefreshCw, Wallet, CalendarClock, Inbox,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  purchases, suppliers as suppliersApi, products as productsApi, adminEtl,
  type ParsedInvoice, type ParsedItem, type Supplier, type SupplierIn,
  type PurchaseSummary, type PurchasePaymentMethod, PURCHASE_PAYMENT_METHOD_LABELS,
  type InboxInvoice,
} from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { Pagination } from '@/components/ui/pagination';

type Tab = 'historial' | 'cartera' | 'correo' | 'nueva-xml' | 'nueva-manual';
/** Factura que viene del correo, ya leída: se abre directo en el paso de revisión */
type DesdeCorreo = { id: string; parsed: ParsedInvoice; etiqueta: string };
type Step = 1 | 2 | 3;

function PaymentMethodSelect({
  value, onChange,
}: { value: PurchasePaymentMethod; onChange: (v: PurchasePaymentMethod) => void }) {
  return (
    <select
      className="w-full border rounded px-3 py-2"
      value={value}
      onChange={(e) => onChange(e.target.value as PurchasePaymentMethod)}
    >
      {(Object.keys(PURCHASE_PAYMENT_METHOD_LABELS) as PurchasePaymentMethod[]).map((m) => (
        <option key={m} value={m}>{PURCHASE_PAYMENT_METHOD_LABELS[m]}</option>
      ))}
    </select>
  );
}

function PaymentStatusBadge({ status, dueDate }: { status: string; dueDate: string | null }) {
  if (status !== 'pendiente') return <Badge className="bg-green-100 text-green-700">Pagada</Badge>;
  const vencida = dueDate ? new Date(dueDate + 'T23:59:59') < new Date() : false;
  return (
    <Badge className={vencida ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}>
      {vencida ? 'Vencida' : 'Pendiente'}{dueDate ? ` · ${new Date(dueDate + 'T00:00:00').toLocaleDateString('es-CO')}` : ''}
    </Badge>
  );
}

interface EditableItem extends ParsedItem {
  _id: string;
  factor_pack: number;
  margen_pct: number;
}

const DEFAULT_MARGIN = 20;

// ─── Matemática de la factura (26-sep-2026) ─────────────────────────
// Diego: "facturas con descuento al final o por línea… no lo está teniendo en
// cuenta al subir el XML". Una sola fuente de verdad para la grilla, los totales
// y lo que se guarda. Norma DIAN UBL 2.1:
//   neto de línea  = cantidad × costo unitario − descuento $ + cargos
//   IVA de línea   = neto × IVA %
//   total factura  = Σ(neto + IVA) − descuento global + cargos globales
// El descuento global no cambia la base del IVA de cada línea: se reparte al final
// en proporción al valor con IVA de cada producto.
const r2 = (n: number) => Math.round(n * 100) / 100;
const lineaBruta = (it: EditableItem) => it.cantidad * it.costo_base_unitario;
const lineaNeta = (it: EditableItem) => Math.max(0, lineaBruta(it) - (it.descuento || 0) + (it.cargos || 0));
const lineaConIva = (it: EditableItem) => lineaNeta(it) * (1 + (it.iva_pct || 0) / 100);

function totalesFactura(items: EditableItem[], descGlobal: number, cargosGlobal: number) {
  const bruto = items.reduce((s, it) => s + lineaBruta(it), 0);
  const descLineas = items.reduce((s, it) => s + (it.descuento || 0), 0);
  const cargosLineas = items.reduce((s, it) => s + (it.cargos || 0), 0);
  const base = items.reduce((s, it) => s + lineaNeta(it), 0);
  const iva = items.reduce((s, it) => s + lineaNeta(it) * (it.iva_pct || 0) / 100, 0);
  const total = base + iva - (descGlobal || 0) + (cargosGlobal || 0);
  return { bruto, descLineas, cargosLineas, base, iva, total };
}

/** Costo unitario SIN IVA que se guarda: neto de la línea + su parte del descuento/cargo
 *  global + su parte del transporte (todo repartido por valor con IVA). El backend le
 *  suma el IVA (no somos responsables de IVA: es costo real). */
function costoUnitarioFinal(
  it: EditableItem, todos: EditableItem[], descGlobal: number, cargosGlobal: number, transporte: number,
) {
  const baseReparto = todos.reduce((s, x) => s + lineaConIva(x), 0);
  const peso = baseReparto > 0 ? lineaConIva(it) / baseReparto : 0;
  const conIvaFinal = lineaConIva(it) + peso * ((cargosGlobal || 0) - (descGlobal || 0) + (transporte || 0));
  const unidades = it.cantidad || 1;
  return r2(conIvaFinal / (1 + (it.iva_pct || 0) / 100) / unidades);
}

export default function PurchasesPage() {
  const [tab, setTab] = useState<Tab>('historial');
  const [desdeCorreo, setDesdeCorreo] = useState<DesdeCorreo | null>(null);
  const qc = useQueryClient();
  const pendientesQ = useQuery({ queryKey: ['inbox', 'pendiente'], queryFn: () => purchases.inbox.list('pendiente'), refetchInterval: 120_000 });
  const nPendientes = pendientesQ.data?.conteo?.pendiente ?? 0;
  const bootstrapMut = useMutation({
    mutationFn: () => adminEtl.bootstrapSuppliers(),
    onSuccess: (res) => {
      toast.success(`Proveedores creados: ${res.created} nuevos, ${res.skipped} ya existían`);
      qc.invalidateQueries({ queryKey: ['suppliers'] });
    },
    onError: (e: Error) => toast.error(`Error: ${e.message}`),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <ShoppingCart className="h-8 w-8 text-orange-500" />
            Compras a Proveedores
          </h1>
          <p className="text-gray-600 mt-1">Carga facturas DIAN, asocia productos y genera órdenes</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => bootstrapMut.mutate()}
          disabled={bootstrapMut.isPending}
          className="text-orange-600 border-orange-300 hover:bg-orange-50"
        >
          <RefreshCw className="w-4 h-4 mr-1" />
          {bootstrapMut.isPending ? 'Importando…' : 'Importar proveedores legados'}
        </Button>
      </div>

      <div className="flex gap-2 border-b">
        {[
          { id: 'historial', label: 'Historial', icon: FileText },
          { id: 'cartera', label: 'Cartera con proveedores', icon: Wallet },
          { id: 'correo', label: 'Facturas por cargar', icon: Inbox, badge: nPendientes },
          { id: 'nueva-xml', label: 'Nueva con XML DIAN', icon: FileUp },
          { id: 'nueva-manual', label: 'Nueva manual', icon: Edit2 },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => { setTab(t.id as Tab); if (t.id === 'nueva-xml') setDesdeCorreo(null); }}
            className={`px-4 py-2 font-medium border-b-2 transition flex items-center gap-2 ${
              tab === t.id ? 'border-orange-500 text-orange-600' : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <t.icon className="h-4 w-4" />{t.label}
            {'badge' in t && (t as { badge?: number }).badge ? (
              <span className="ml-1 min-w-5 h-5 px-1.5 rounded-full bg-orange-500 text-white text-xs flex items-center justify-center">
                {(t as { badge?: number }).badge}
              </span>
            ) : null}
          </button>
        ))}
      </div>

      {tab === 'historial' && <HistorialTab />}
      {tab === 'cartera' && <CarteraTab />}
      {tab === 'correo' && (
        <FacturasCorreoTab onCargar={(d) => { setDesdeCorreo(d); setTab('nueva-xml'); }} />
      )}
      {tab === 'nueva-xml' && (
        <NuevaXmlTab
          key={desdeCorreo?.id ?? 'manual'}
          inicial={desdeCorreo}
          onDone={() => {
            const venia = !!desdeCorreo;
            setDesdeCorreo(null);
            setTab(venia ? 'correo' : 'historial');
          }}
        />
      )}
      {tab === 'nueva-manual' && <NuevaManualTab onDone={() => setTab('historial')} />}
    </div>
  );
}

// ─── FACTURAS POR CARGAR (bandeja del correo) ─────────────────────
// Las facturas DIAN que llegan a bigotesypaticasdosquebradas@ se leen solas (solo
// lectura) cada 5 min. Aquí se revisan: "Cargar" abre el flujo normal de ingreso
// por XML ya con la factura leída; al guardar queda marcada como cargada.
const FILTROS_CORREO: { id: 'pendiente' | 'ya_ingresada' | 'cargada' | 'descartada' | 'otros' | 'todas'; label: string }[] = [
  { id: 'pendiente', label: 'Por cargar' },
  { id: 'ya_ingresada', label: 'Ya ingresadas a mano' },
  { id: 'cargada', label: 'Cargadas' },
  { id: 'descartada', label: 'Descartadas' },
  { id: 'otros', label: 'No son mercancía' },
  { id: 'todas', label: 'Todas' },
];

function FacturasCorreoTab({ onCargar }: { onCargar: (d: DesdeCorreo) => void }) {
  const qc = useQueryClient();
  const [filtro, setFiltro] = useState<(typeof FILTROS_CORREO)[number]['id']>('pendiente');
  const [abriendo, setAbriendo] = useState<string | null>(null);
  const q = useQuery({ queryKey: ['inbox', filtro], queryFn: () => purchases.inbox.list(filtro) });

  const syncMut = useMutation({
    mutationFn: (dias: number) => purchases.inbox.sync(dias),
    onSuccess: (r) => {
      toast.success(r.nuevos ? `Correo revisado: ${r.nuevos} documento(s) nuevo(s)` : 'Correo revisado: no hay facturas nuevas');
      qc.invalidateQueries({ queryKey: ['inbox'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const estadoMut = useMutation({
    mutationFn: (v: { id: string; estado: 'descartada' | 'pendiente' }) => purchases.inbox.setEstado(v.id, { estado: v.estado }),
    onSuccess: (_r, v) => {
      toast.success(v.estado === 'descartada' ? 'Factura descartada' : 'Factura devuelta a "por cargar"');
      qc.invalidateQueries({ queryKey: ['inbox'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  async function cargar(f: InboxInvoice) {
    setAbriendo(f.id);
    try {
      const parsed = await purchases.inbox.parse(f.id);
      onCargar({ id: f.id, parsed, etiqueta: `${f.supplier_name} · ${f.folio ?? ''}` });
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setAbriendo(null);
    }
  }

  const items = q.data?.items ?? [];
  const conteo = q.data?.conteo ?? {};
  const totalPend = items.filter((i) => i.estado === 'pendiente' && i.doc_type === '01').reduce((a, i) => a + (i.total ?? 0), 0);

  return (
    <div className="space-y-4">
      <Card className="p-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold flex items-center gap-2"><Inbox className="h-5 w-5 text-orange-500" /> Facturas que llegaron al correo</p>
          <p className="text-sm text-gray-600">
            Se leen solas cada 5 minutos desde bigotesypaticasdosquebradas@ (solo lectura). Toca <b>Cargar</b> para revisarla y guardarla como compra.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => syncMut.mutate(3)} disabled={syncMut.isPending}>
            <RefreshCw className={`w-4 h-4 mr-1 ${syncMut.isPending ? 'animate-spin' : ''}`} /> Revisar correo ahora
          </Button>
          <Button variant="outline" size="sm" onClick={() => syncMut.mutate(120)} disabled={syncMut.isPending}>
            Traer últimos 4 meses
          </Button>
        </div>
      </Card>

      <div className="flex flex-wrap gap-2">
        {FILTROS_CORREO.map((f) => (
          <button
            key={f.id}
            onClick={() => setFiltro(f.id)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium border transition ${
              filtro === f.id ? 'bg-orange-500 text-white border-orange-500' : 'bg-white text-gray-700 border-gray-200 hover:border-orange-300'
            }`}
          >
            {f.label}{f.id !== 'todas' && conteo[f.id] ? ` (${conteo[f.id]})` : ''}
          </button>
        ))}
      </div>

      {filtro === 'pendiente' && items.length > 0 && (
        <p className="text-sm text-gray-600">
          {items.filter((i) => i.doc_type === '01').length} factura(s) por cargar · total {formatCurrency(totalPend)}
        </p>
      )}

      {q.isLoading ? (
        <Card className="p-8 text-center text-gray-500">Cargando…</Card>
      ) : items.length === 0 ? (
        <Card className="p-10 text-center text-gray-500">
          <CheckCircle2 className="h-10 w-10 mx-auto text-green-500 mb-2" />
          {filtro === 'pendiente' ? 'No hay facturas pendientes por cargar.' : 'No hay documentos en este filtro.'}
        </Card>
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="text-left p-3">Fecha</th>
                <th className="text-left p-3">Proveedor</th>
                <th className="text-left p-3">Factura</th>
                <th className="text-right p-3">Subtotal</th>
                <th className="text-right p-3">IVA</th>
                <th className="text-right p-3">Total</th>
                <th className="text-right p-3"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((f) => (
                <tr key={f.id} className="border-t">
                  <td className="p-3 whitespace-nowrap">{f.issue_date ?? '—'}</td>
                  <td className="p-3">
                    <div className="font-medium">{f.supplier_name}</div>
                    <div className="text-xs text-gray-500 flex flex-wrap gap-1 items-center">
                      NIT {f.nit}
                      {!f.proveedor_registrado && f.estado !== 'otros' && <Badge className="bg-amber-100 text-amber-800 text-[10px]">proveedor nuevo</Badge>}
                    </div>
                  </td>
                  <td className="p-3">
                    <div className="font-mono">{f.folio ?? '—'}</div>
                    {f.doc_type !== '01' && <Badge className="mt-1 bg-purple-100 text-purple-700 text-[10px]">{f.tipo}</Badge>}
                    {f.nota && <div className="text-xs text-gray-500 mt-0.5">{f.nota}</div>}
                  </td>
                  <td className="p-3 text-right whitespace-nowrap">{f.subtotal != null ? formatCurrency(f.subtotal) : '—'}</td>
                  <td className="p-3 text-right whitespace-nowrap">{f.tax_amount != null ? formatCurrency(f.tax_amount) : '—'}</td>
                  <td className="p-3 text-right whitespace-nowrap font-semibold">{f.total != null ? formatCurrency(f.total) : '—'}</td>
                  <td className="p-3 text-right whitespace-nowrap">
                    <div className="flex justify-end gap-2">
                      {f.doc_type === '01' && (f.estado === 'pendiente' || f.estado === 'descartada') && (
                        <Button size="sm" onClick={() => cargar(f)} disabled={abriendo === f.id} className="bg-orange-500 hover:bg-orange-600 text-white">
                          {abriendo === f.id ? 'Abriendo…' : 'Cargar'}
                        </Button>
                      )}
                      {f.estado === 'pendiente' && (
                        <Button size="sm" variant="outline" onClick={() => estadoMut.mutate({ id: f.id, estado: 'descartada' })}>
                          Descartar
                        </Button>
                      )}
                      {f.estado === 'descartada' && (
                        <Button size="sm" variant="outline" onClick={() => estadoMut.mutate({ id: f.id, estado: 'pendiente' })}>
                          Restaurar
                        </Button>
                      )}
                      {(f.estado === 'cargada' || f.estado === 'ya_ingresada') && (
                        <Badge className="bg-green-100 text-green-700">{f.estado === 'cargada' ? 'Cargada' : 'Ya estaba ingresada'}</Badge>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

// ─── HISTORIAL ────────────────────────────────────────────────────
function HistorialTab() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [viewing, setViewing] = useState<string | null>(null);

  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['purchases', search, page],
    queryFn: () => purchases.list({ q: search || undefined, page, page_size: 20 }),
  });

  const stats = useQuery({ queryKey: ['purchases-stats'], queryFn: () => purchases.stats() });

  const markPaidMut = useMutation({
    mutationFn: (id: string) => purchases.markPaid(id),
    onSuccess: () => {
      toast.success('Compra marcada como pagada');
      qc.invalidateQueries({ queryKey: ['purchases'] });
      qc.invalidateQueries({ queryKey: ['purchases-cartera'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <p className="text-sm text-gray-500">Gasto del mes</p>
          <p className="text-2xl font-bold">{formatCurrency(stats.data?.total_spend_month || 0)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Compras del mes</p>
          <p className="text-2xl font-bold">{stats.data?.total_count_month || 0}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Top proveedor</p>
          <p className="text-lg font-bold truncate">{stats.data?.top_suppliers?.[0]?.supplier_name || '—'}</p>
        </Card>
      </div>

      <Card className="p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Buscar por folio o proveedor..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-10"
          />
        </div>
      </Card>

      <Card>
        {isLoading ? (
          <div className="p-12 text-center text-gray-500">Cargando...</div>
        ) : !data?.items.length ? (
          <div className="p-12 text-center text-gray-500">No hay compras registradas</div>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">Fecha</th>
                  <th className="text-left p-3">Folio</th>
                  <th className="text-left p-3">Proveedor</th>
                  <th className="text-right p-3">Items</th>
                  <th className="text-right p-3">Total</th>
                  <th className="text-center p-3">Estado</th>
                  <th className="text-center p-3">Pago</th>
                  <th className="text-center p-3"></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((p: PurchaseSummary) => (
                  <tr key={p.id} className="border-t hover:bg-gray-50">
                    <td className="p-3">{new Date(p.purchased_at).toLocaleDateString('es-CO')}</td>
                    <td className="p-3 font-mono text-xs">{p.folio || '—'}</td>
                    <td className="p-3">{p.supplier_name}</td>
                    <td className="p-3 text-right">{p.items_count}</td>
                    <td className="p-3 text-right font-bold">{formatCurrency(p.total)}</td>
                    <td className="p-3 text-center">
                      <Badge className={
                        p.status === 'received' ? 'bg-green-100 text-green-700' :
                        p.status === 'draft' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-700'
                      }>{p.status}</Badge>
                    </td>
                    <td className="p-3 text-center">
                      <div className="flex flex-col items-center gap-1">
                        <span className="text-xs text-gray-500">{PURCHASE_PAYMENT_METHOD_LABELS[p.payment_method]}</span>
                        <PaymentStatusBadge status={p.payment_status} dueDate={p.due_date} />
                        {p.payment_status === 'pendiente' && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-green-700 border-green-300 hover:bg-green-50 h-6 px-2 text-xs"
                            disabled={markPaidMut.isPending}
                            onClick={() => markPaidMut.mutate(p.id)}
                          >
                            Marcar pagada
                          </Button>
                        )}
                      </div>
                    </td>
                    <td className="p-3 text-center">
                      <Button size="sm" variant="outline" onClick={() => setViewing(p.id)}>
                        <Eye className="h-3 w-3" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {data && data.total > data.page_size && (
        <Pagination page={page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
      )}

      {viewing && <PurchaseDetailDialog id={viewing} onClose={() => setViewing(null)} />}
    </div>
  );
}

function PurchaseDetailDialog({ id, onClose }: { id: string; onClose: () => void }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['purchase', id], queryFn: () => purchases.get(id) });
  const markPaidMut = useMutation({
    mutationFn: () => purchases.markPaid(id),
    onSuccess: () => {
      toast.success('Compra marcada como pagada');
      qc.invalidateQueries({ queryKey: ['purchase', id] });
      qc.invalidateQueries({ queryKey: ['purchases'] });
      qc.invalidateQueries({ queryKey: ['purchases-cartera'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  return (
    <Dialog open onClose={onClose} title={data ? `Compra ${data.folio || data.id.slice(0, 8)}` : 'Compra'} size="lg">
      <DialogBody>
        {isLoading ? (
          <div className="text-center py-8">Cargando...</div>
        ) : data ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-gray-500">Proveedor:</span> <strong>{data.supplier_name}</strong></div>
              <div><span className="text-gray-500">Fecha:</span> {new Date(data.purchased_at).toLocaleDateString('es-CO')}</div>
              <div><span className="text-gray-500">Estado:</span> {data.status}</div>
              <div><span className="text-gray-500">Pago:</span> {PURCHASE_PAYMENT_METHOD_LABELS[data.payment_method]}</div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Cartera:</span>
                <PaymentStatusBadge status={data.payment_status} dueDate={data.due_date} />
                {data.payment_status === 'pendiente' && (
                  <Button size="sm" variant="outline" className="text-green-700 border-green-300 hover:bg-green-50" disabled={markPaidMut.isPending} onClick={() => markPaidMut.mutate()}>
                    Marcar pagada
                  </Button>
                )}
              </div>
              {data.paid_at && (
                <div><span className="text-gray-500">Pagada el:</span> {new Date(data.paid_at).toLocaleDateString('es-CO')}</div>
              )}
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-2">Producto</th>
                  <th className="text-right p-2">Cant</th>
                  <th className="text-right p-2">Costo</th>
                  <th className="text-right p-2">Total</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((it) => (
                  <tr key={it.id} className="border-t">
                    <td className="p-2">{it.product_name}</td>
                    <td className="p-2 text-right">{it.quantity}</td>
                    <td className="p-2 text-right">{formatCurrency(it.unit_cost)}</td>
                    <td className="p-2 text-right font-bold">{formatCurrency(it.total_cost)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t font-bold">
                  <td colSpan={3} className="p-2 text-right">Total:</td>
                  <td className="p-2 text-right">{formatCurrency(data.total)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        ) : null}
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cerrar</Button>
      </DialogFooter>
    </Dialog>
  );
}

// ─── CARTERA CON PROVEEDORES ──────────────────────────────────────
function CarteraTab() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['purchases-cartera'], queryFn: () => purchases.cartera() });

  const markPaidMut = useMutation({
    mutationFn: (id: string) => purchases.markPaid(id),
    onSuccess: () => {
      toast.success('Compra marcada como pagada');
      qc.invalidateQueries({ queryKey: ['purchases-cartera'] });
      qc.invalidateQueries({ queryKey: ['purchases'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (isLoading) return <div className="p-12 text-center text-gray-500">Cargando cartera...</div>;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <p className="text-sm text-gray-500 flex items-center gap-1"><Wallet className="h-4 w-4" />Total por pagar</p>
          <p className="text-2xl font-bold">{formatCurrency(data.total_pendiente)}</p>
        </Card>
        <Card className="p-4 border-red-200">
          <p className="text-sm text-gray-500 flex items-center gap-1"><CalendarClock className="h-4 w-4 text-red-500" />Vencido</p>
          <p className="text-2xl font-bold text-red-600">{formatCurrency(data.total_vencido)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Compras a crédito pendientes</p>
          <p className="text-2xl font-bold">{data.items.length}</p>
        </Card>
      </div>

      {data.por_proveedor.length > 0 && (
        <Card className="p-4">
          <h3 className="font-bold mb-3">Por proveedor</h3>
          <div className="flex flex-wrap gap-2">
            {data.por_proveedor.map((p) => (
              <Badge key={p.supplier_name} className="bg-gray-100 text-gray-800 py-1.5 px-3">
                {p.supplier_name}: {formatCurrency(p.total)} ({p.count})
              </Badge>
            ))}
          </div>
        </Card>
      )}

      <Card>
        {data.items.length === 0 ? (
          <div className="p-12 text-center text-gray-500">No hay compras a crédito pendientes de pago 🎉</div>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3">Proveedor</th>
                  <th className="text-left p-3">Folio</th>
                  <th className="text-left p-3">Comprada</th>
                  <th className="text-left p-3">Vence</th>
                  <th className="text-right p-3">Total</th>
                  <th className="text-center p-3">Plazo</th>
                  <th className="text-center p-3"></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((it) => (
                  <tr key={it.id} className={`border-t hover:bg-gray-50 ${it.dias_para_vencer < 0 ? 'bg-red-50' : ''}`}>
                    <td className="p-3 font-medium">{it.supplier_name}</td>
                    <td className="p-3 font-mono text-xs">{it.folio || '—'}</td>
                    <td className="p-3">{new Date(it.purchased_at).toLocaleDateString('es-CO')}</td>
                    <td className="p-3">
                      {new Date(it.due_date + 'T00:00:00').toLocaleDateString('es-CO')}{' '}
                      <span className={it.dias_para_vencer < 0 ? 'text-red-600 font-bold' : 'text-gray-500'}>
                        ({it.dias_para_vencer < 0 ? `vencida hace ${Math.abs(it.dias_para_vencer)}d` : `en ${it.dias_para_vencer}d`})
                      </span>
                    </td>
                    <td className="p-3 text-right font-bold">{formatCurrency(it.total)}</td>
                    <td className="p-3 text-center">
                      <Badge className="bg-blue-100 text-blue-700">{PURCHASE_PAYMENT_METHOD_LABELS[it.payment_method]}</Badge>
                    </td>
                    <td className="p-3 text-center">
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-green-700 border-green-300 hover:bg-green-50"
                        disabled={markPaidMut.isPending}
                        onClick={() => markPaidMut.mutate(it.id)}
                      >
                        Marcar pagada
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

// ─── NUEVA CON XML ────────────────────────────────────────────────
function NuevaXmlTab({ onDone, inicial }: { onDone: () => void; inicial?: DesdeCorreo | null }) {
  const qc = useQueryClient();
  const [step, setStep] = useState<Step>(1);
  const [parsed, setParsed] = useState<ParsedInvoice | null>(null);
  const [items, setItems] = useState<EditableItem[]>([]);
  const [supplierId, setSupplierId] = useState<string>('');
  const [supplierName, setSupplierName] = useState<string>('');
  const [createNewSupplier, setCreateNewSupplier] = useState(false);
  const [newSupplier, setNewSupplier] = useState<SupplierIn>({ nit: '', name: '' });
  const [folio, setFolio] = useState('');
  const [transportCost, setTransportCost] = useState(0);
  const [descGlobal, setDescGlobal] = useState(0);
  const [cargosGlobal, setCargosGlobal] = useState(0);
  const [paymentMethod, setPaymentMethod] = useState<PurchasePaymentMethod>('efectivo');
  const parseMut = useMutation({
    mutationFn: (file: File) => purchases.parseXml(file),
    onSuccess: (data) => aplicarParsed(data),
    onError: (e: Error) => toast.error(e.message),
  });

  // Factura del correo: ya viene leída por el MISMO parser → directo al paso 2 (revisión)
  useEffect(() => {
    if (inicial) aplicarParsed(inicial.parsed);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inicial?.id]);

  function aplicarParsed(data: ParsedInvoice) {
      setParsed(data);
      setFolio(data.folio || '');
      if (data.supplier.matched_supplier_id) {
        setSupplierId(data.supplier.matched_supplier_id);
        setSupplierName(data.supplier.name || '');
      } else if (data.supplier.nit) {
        setCreateNewSupplier(true);
        setNewSupplier({
          nit: data.supplier.nit,
          name: data.supplier.name || '',
          email: data.supplier.email || '',
          phone: data.supplier.phone || '',
          address: data.supplier.address || '',
        });
      }
      setItems(data.items.map((it, i) => ({
        ...it,
        descuento: it.descuento || 0,
        descuento_pct: it.descuento_pct || 0,
        cargos: it.cargos || 0,
        _id: `item-${i}`,
        factor_pack: Math.max(1, it.factor_sugerido || 1),
        margen_pct: DEFAULT_MARGIN,
      })));
      setDescGlobal(data.descuento_global || 0);
      setCargosGlobal(data.cargos_globales || 0);
      setStep(2);
      const conDesc = data.items.filter((it) => (it.descuento || 0) > 0).length;
      toast.success(
        `XML procesado: ${data.items.length} items` +
        (conDesc ? ` · ${conDesc} con descuento por línea` : '') +
        (data.descuento_global ? ` · descuento global ${formatCurrency(data.descuento_global)}` : ''),
      );
      if (data.aviso) toast.warning(data.aviso, { duration: 12000 });
      const empaques = data.items.filter((it) => (it.factor_sugerido || 1) > 1).length;
      if (empaques) toast.info(`${empaques} producto(s) vienen por empaque y se ingresan por unidad: revisa "Und/emp."`);
  }

  const saveMut = useMutation({
    mutationFn: async () => {
      let finalSupplierId = supplierId;
      let finalSupplierName = supplierName;

      if (createNewSupplier) {
        if (!newSupplier.name.trim()) throw new Error('El nombre del proveedor es requerido');
        const created = await suppliersApi.create(newSupplier);
        finalSupplierId = created.id;
        finalSupplierName = created.name;
      }

      const effectiveName = finalSupplierName || newSupplier.name;
      if (!effectiveName.trim()) throw new Error('Selecciona o crea un proveedor antes de guardar');

      const matchedItems = items.filter((it) => it.suggested_product_id);
      if (matchedItems.length === 0) throw new Error('Debes asociar al menos un producto antes de guardar');

      // Cuadre contra la factura antes de guardar: si no cuadra, preguntar.
      const t = totalesFactura(items, descGlobal, cargosGlobal);
      const ref = parsed?.xml_consistente ? parsed.xml_total_factura : 0;
      if (ref > 0 && Math.abs(t.total - ref) > 100) {
        const ok = window.confirm(
          `El total calculado (${formatCurrency(t.total)}) no cuadra con la factura (${formatCurrency(ref)}): ` +
          `diferencia ${formatCurrency(t.total - ref)}. ¿Guardar de todas formas?`,
        );
        if (!ok) throw new Error('Guardado cancelado: revisa costos y descuentos');
      }

      return purchases.create({
        folio: folio || undefined,
        supplier_id: finalSupplierId || undefined,
        supplier_name: effectiveName,
        payment_method: paymentMethod,
        items: matchedItems
          .map((it) => ({
            product_id: it.suggested_product_id!,
            sku_proveedor: it.sku_proveedor || undefined,
            sku_interno: it.suggested_product_sku || undefined,
            product_name: it.suggested_product_name || it.descripcion,
            quantity: Math.round(it.cantidad),
            factor_pack: it.factor_pack,
            // neto después de descuentos (línea + global) y con su parte del transporte
            unit_cost: costoUnitarioFinal(it, items, descGlobal, cargosGlobal, transportCost),
            tax_pct: it.iva_pct,
          })),
        receive_now: true,
      });
    },
    onSuccess: async (compra) => {
      toast.success('Compra registrada correctamente');
      if (inicial) {
        // la factura del correo queda como cargada, enlazada a la compra creada
        try {
          await purchases.inbox.setEstado(inicial.id, { estado: 'cargada', purchase_id: compra.id });
        } catch {
          toast.warning('La compra se guardó, pero no se pudo marcar la factura como cargada en la bandeja');
        }
        qc.invalidateQueries({ queryKey: ['inbox'] });
      }
      qc.invalidateQueries({ queryKey: ['purchases'] });
      qc.invalidateQueries({ queryKey: ['inventory'] });
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const totals = useMemo(() => {
    const t = totalesFactura(items, descGlobal, cargosGlobal);
    const ref = parsed?.xml_consistente ? parsed.xml_total_factura : 0;
    return { ...t, ref, diff: ref > 0 ? t.total - ref : 0, inventario: t.total + (transportCost || 0) };
  }, [items, descGlobal, cargosGlobal, transportCost, parsed]);
  const cuadra = totals.ref > 0 && Math.abs(totals.diff) <= 100;

  const unmatchedCount = items.filter((it) => !it.suggested_product_id).length;

  return (
    <div className="space-y-4">
      {inicial && (
        <Card className="p-3 bg-orange-50 border-orange-200 text-sm text-orange-900 flex items-center gap-2">
          <Inbox className="h-4 w-4" /> Factura del correo: <b>{inicial.etiqueta}</b>. Revisa, asocia y guarda como siempre.
        </Card>
      )}
      <Card className="p-4">
        <div className="flex items-center gap-2">
          {[1, 2, 3].map((n) => (
            <div key={n} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                step >= n ? 'bg-orange-500 text-white' : 'bg-gray-200 text-gray-500'
              }`}>{n}</div>
              <span className={step === n ? 'font-bold' : 'text-gray-500'}>
                {n === 1 ? 'Cargar XML' : n === 2 ? 'Revisar y Asociar' : 'Confirmar'}
              </span>
              {n < 3 && <div className="w-12 h-0.5 bg-gray-300" />}
            </div>
          ))}
        </div>
      </Card>

      {step === 1 && (
        <Card className="p-12 text-center">
          <FileUp className="h-16 w-16 mx-auto text-orange-500 mb-4" />
          <h3 className="text-xl font-bold mb-2">Sube el XML de la factura DIAN</h3>
          <p className="text-gray-600 mb-6">Soporta formato Invoice o AttachedDocument (UBL)</p>
          <label
            htmlFor="xml-upload-input"
            className={`inline-flex items-center gap-2 px-6 py-3 rounded-lg font-semibold cursor-pointer transition
              ${parseMut.isPending
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-orange-500 hover:bg-orange-600 text-white'}`}
          >
            <Upload className="h-4 w-4" />
            {parseMut.isPending ? 'Procesando XML...' : 'Seleccionar archivo XML'}
          </label>
          <input
            id="xml-upload-input"
            type="file"
            accept=".xml,text/xml,application/xml"
            className="sr-only"
            disabled={parseMut.isPending}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                parseMut.mutate(file);
                e.target.value = '';
              }
            }}
          />
        </Card>
      )}

      {step === 2 && parsed && (
        <>
          <Card className="p-4">
            <h3 className="font-bold mb-3 flex items-center gap-2"><Truck className="h-4 w-4" />Proveedor</h3>
            {parsed.supplier.matched_supplier_id ? (
              <div className="bg-green-50 border border-green-200 rounded p-3 flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                <div>
                  <p className="font-bold text-green-900">{supplierName}</p>
                  <p className="text-xs text-green-700">Proveedor existente reconocido por NIT {parsed.supplier.nit}</p>
                </div>
              </div>
            ) : createNewSupplier ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded p-3 space-y-2">
                <div className="flex items-center gap-2 text-yellow-900">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="font-bold">Proveedor nuevo — se creará al guardar</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Input placeholder="NIT" value={newSupplier.nit} onChange={(e) => setNewSupplier({ ...newSupplier, nit: e.target.value })} />
                  <Input placeholder="Nombre" value={newSupplier.name} onChange={(e) => setNewSupplier({ ...newSupplier, name: e.target.value })} />
                  <Input placeholder="Email" value={newSupplier.email || ''} onChange={(e) => setNewSupplier({ ...newSupplier, email: e.target.value })} />
                  <Input placeholder="Teléfono" value={newSupplier.phone || ''} onChange={(e) => setNewSupplier({ ...newSupplier, phone: e.target.value })} />
                </div>
              </div>
            ) : null}

            <div className="grid grid-cols-3 gap-3 mt-3">
              <div>
                <label className="text-sm">Folio factura</label>
                <Input value={folio} onChange={(e) => setFolio(e.target.value)} />
              </div>
              <div>
                <label className="text-sm">Medio de pago</label>
                <PaymentMethodSelect value={paymentMethod} onChange={setPaymentMethod} />
              </div>
              <div>
                <label className="text-sm">Transporte (no está en la factura)</label>
                <Input type="number" value={transportCost} onChange={(e) => setTransportCost(Number(e.target.value) || 0)} />
              </div>
            </div>
          </Card>

          {parsed.aviso && (
            <Card className="p-3 bg-amber-50 border-amber-300 text-sm text-amber-900 flex gap-2">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>{parsed.aviso}</span>
            </Card>
          )}

          <Card className="p-4">
            <h3 className="font-bold mb-3">Cuadre con la factura</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
              <div className="space-y-1">
                <div className="flex justify-between"><span className="text-gray-500">Subtotal bruto</span><span>{formatCurrency(totals.bruto)}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">− Descuentos por línea</span><span className="text-red-600">{formatCurrency(-totals.descLineas)}</span></div>
                {totals.cargosLineas > 0 && (
                  <div className="flex justify-between"><span className="text-gray-500">+ Cargos por línea</span><span>{formatCurrency(totals.cargosLineas)}</span></div>
                )}
                <div className="flex justify-between font-medium border-t pt-1"><span>Base neta</span><span>{formatCurrency(totals.base)}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">+ IVA</span><span>{formatCurrency(totals.iva)}</span></div>
              </div>
              <div>
                <label className="text-sm text-gray-600">− Descuento global de la factura ($)</label>
                <Input type="number" value={descGlobal} onChange={(e) => setDescGlobal(Number(e.target.value) || 0)} />
                {parsed.descuento_global_declarado > 0 && parsed.descuento_global_declarado !== parsed.descuento_global && (
                  <p className="text-xs text-gray-500 mt-1">
                    El XML declara {formatCurrency(parsed.descuento_global_declarado)}, pero ya está compensado en el IVA
                    de la factura: el valor real a restar es {formatCurrency(parsed.descuento_global)}.
                  </p>
                )}
              </div>
              <div>
                <label className="text-sm text-gray-600">+ Cargos globales ($)</label>
                <Input type="number" value={cargosGlobal} onChange={(e) => setCargosGlobal(Number(e.target.value) || 0)} />
                <p className="text-xs text-gray-500 mt-1">Fletes o recargos que el proveedor cobra al final.</p>
              </div>
              <div className={`rounded-lg p-3 border ${
                totals.ref <= 0 ? 'bg-gray-50 border-gray-200' : cuadra ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'
              }`}>
                <div className="flex justify-between font-bold"><span>Total calculado</span><span>{formatCurrency(totals.total)}</span></div>
                <div className="flex justify-between text-gray-600"><span>Total de la factura</span><span>{totals.ref > 0 ? formatCurrency(totals.ref) : '—'}</span></div>
                {totals.ref > 0 && (
                  <p className={`mt-1 font-semibold flex items-center gap-1 ${cuadra ? 'text-green-700' : 'text-red-700'}`}>
                    {cuadra ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                    {cuadra ? 'Cuadra con la factura' : `Diferencia ${formatCurrency(totals.diff)}`}
                  </p>
                )}
                {parsed.xml_anticipo > 0 && (
                  <p className="text-xs text-gray-500 mt-1">Anticipo ya pagado: {formatCurrency(parsed.xml_anticipo)} (no baja el costo).</p>
                )}
                {transportCost > 0 && (
                  <p className="text-xs text-gray-600 mt-1">Costo a inventario con transporte: {formatCurrency(totals.inventario)}</p>
                )}
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold">Items ({items.length}) — Asociación inteligente</h3>
              {unmatchedCount > 0 && (
                <Badge className="bg-red-100 text-red-700">
                  <AlertTriangle className="h-3 w-3 mr-1" />{unmatchedCount} sin asociar
                </Badge>
              )}
            </div>

            <div className="overflow-auto max-h-[500px]">
              <table className="w-full text-xs">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="text-left p-2">SKU Prov</th>
                    <th className="text-left p-2">Descripción XML</th>
                    <th className="text-right p-2">Cant</th>
                    <th className="text-right p-2" title="Unidades que trae cada empaque (caja x 30 sobres = 30)">Und/emp.</th>
                    <th className="text-right p-2">Costo unit.</th>
                    <th className="text-right p-2">Desc %</th>
                    <th className="text-right p-2">Desc $</th>
                    <th className="text-right p-2">IVA %</th>
                    <th className="text-right p-2">Neto unit.</th>
                    <th className="text-right p-2">Total c/IVA</th>
                    <th className="text-right p-2" title="Unidades que entran al inventario y costo de cada una con IVA">A inventario</th>
                    <th className="text-left p-2">Producto Asociado</th>
                    <th className="text-center p-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <ItemRow
                      key={it._id}
                      item={it}
                      onChange={(updated) => setItems(items.map(x => x._id === it._id ? updated : x))}
                      onRemove={() => setItems(items.filter(x => x._id !== it._id))}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(1)}>Atrás</Button>
            <Button onClick={() => setStep(3)} className="bg-orange-500 hover:bg-orange-600">
              Siguiente: Confirmar
            </Button>
          </div>
        </>
      )}

      {step === 3 && (
        <Card className="p-6 space-y-4">
          <h3 className="text-xl font-bold flex items-center gap-2">
            <CheckCircle2 className="h-6 w-6 text-green-600" />Confirmación
          </h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div><strong>Proveedor:</strong> {createNewSupplier ? newSupplier.name : supplierName}</div>
            <div><strong>Folio:</strong> {folio || '—'}</div>
            <div><strong>Items asociados:</strong> {items.filter(i => i.suggested_product_id).length} / {items.length}</div>
            <div>
              <strong>Total factura:</strong> {formatCurrency(totals.total)}{' '}
              {totals.ref > 0 && (cuadra
                ? <span className="text-green-700">✓ cuadra</span>
                : <span className="text-red-700">✗ diferencia {formatCurrency(totals.diff)}</span>)}
            </div>
            {transportCost > 0 && <div><strong>Con transporte:</strong> {formatCurrency(totals.inventario)}</div>}
          </div>

          {unmatchedCount > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm">
              <AlertTriangle className="h-4 w-4 inline text-yellow-700" /> Hay {unmatchedCount} items sin producto asociado. Solo se guardarán los asociados.
            </div>
          )}

          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(2)}>Atrás</Button>
            <Button onClick={() => saveMut.mutate()} disabled={saveMut.isPending} className="bg-green-600 hover:bg-green-700">
              <Save className="h-4 w-4 mr-2" />
              {saveMut.isPending ? 'Guardando...' : 'Confirmar y registrar compra'}
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}

function ItemRow({ item, onChange, onRemove }: { item: EditableItem; onChange: (i: EditableItem) => void; onRemove: () => void }) {
  const [picking, setPicking] = useState(false);

  const matchBadge = () => {
    if (!item.match_reason) return <Badge className="bg-red-100 text-red-700">Sin asociar</Badge>;
    const colorMap: Record<string, string> = {
      memoria: 'bg-green-100 text-green-700',
      sku_exacto: 'bg-blue-100 text-blue-700',
      nombre_exacto: 'bg-blue-100 text-blue-700',
      fuzzy: 'bg-yellow-100 text-yellow-700',
    };
    const cls = colorMap[item.match_reason] || 'bg-gray-100 text-gray-700';
    const label = item.match_reason === 'memoria' ? '🧠 Memoria'
      : item.match_reason === 'sku_exacto' ? '🎯 SKU exacto'
      : item.match_reason === 'nombre_exacto' ? '🎯 Nombre exacto'
      : item.match_reason === 'fuzzy' ? `🔍 ${Math.round((item.match_score || 0) * 100)}%`
      : item.match_reason;
    return <Badge className={cls}>{label}</Badge>;
  };

  return (
    <>
      <tr className="border-t">
        <td className="p-2 font-mono">{item.sku_proveedor || '—'}</td>
        <td className="p-2 max-w-[220px]">
          <p className="truncate" title={item.descripcion}>{item.descripcion}</p>
          {item.factor_pack > 1 && item.factor_motivo && (
            <p className="text-[10px] text-orange-700">📦 x{item.factor_pack}: {item.factor_motivo}</p>
          )}
          {item.factor_pack === 1 && item.factor_alerta && (
            <p className="text-[10px] text-amber-700">⚠️ {item.factor_alerta}</p>
          )}
        </td>
        <td className="p-1 text-right">
          <Input
            type="number" min={1} className="h-8 w-16 text-right text-xs" value={item.cantidad}
            onChange={(e) => {
              const cantidad = Math.max(1, Math.round(Number(e.target.value) || 1));
              // el % se mantiene; el $ se recalcula con la nueva cantidad
              const descuento = r2(cantidad * item.costo_base_unitario * (item.descuento_pct || 0) / 100);
              onChange({ ...item, cantidad, descuento });
            }}
          />
        </td>
        <td className="p-1 text-right">
          <Input
            type="number" min={1} className={`h-8 w-16 text-right text-xs ${item.factor_pack > 1 ? 'border-orange-400 bg-orange-50' : ''}`}
            value={item.factor_pack}
            title={item.factor_motivo || 'Unidades que trae cada empaque'}
            onChange={(e) => onChange({ ...item, factor_pack: Math.max(1, Math.round(Number(e.target.value) || 1)) })}
          />
        </td>
        <td className="p-1 text-right">
          <Input
            type="number" className="h-8 w-28 text-right text-xs" value={r2(item.costo_base_unitario)}
            onChange={(e) => {
              const costo = Number(e.target.value) || 0;
              // el % del proveedor se mantiene: el $ se recalcula con el nuevo costo
              const descuento = item.descuento_pct > 0 ? r2(item.cantidad * costo * item.descuento_pct / 100) : item.descuento;
              onChange({ ...item, costo_base_unitario: costo, descuento });
            }}
          />
        </td>
        <td className="p-1 text-right">
          <Input
            type="number" className="h-8 w-16 text-right text-xs" value={r2(item.descuento_pct)}
            onChange={(e) => {
              const pct = Math.min(100, Math.max(0, Number(e.target.value) || 0));
              onChange({ ...item, descuento_pct: pct, descuento: r2(lineaBruta(item) * pct / 100) });
            }}
          />
        </td>
        <td className="p-1 text-right">
          <Input
            type="number" className="h-8 w-24 text-right text-xs" value={r2(item.descuento)}
            onChange={(e) => {
              const valor = Math.max(0, Number(e.target.value) || 0);
              const bruto = lineaBruta(item);
              onChange({ ...item, descuento: valor, descuento_pct: bruto > 0 ? (valor / bruto) * 100 : 0 });
            }}
          />
        </td>
        <td className="p-1 text-right">
          <Input
            type="number" className="h-8 w-16 text-right text-xs" value={item.iva_pct}
            onChange={(e) => onChange({ ...item, iva_pct: Math.max(0, Number(e.target.value) || 0) })}
          />
        </td>
        <td className="p-2 text-right font-medium">{formatCurrency(item.cantidad > 0 ? lineaNeta(item) / item.cantidad : 0)}</td>
        <td className="p-2 text-right">{formatCurrency(lineaConIva(item))}</td>
        <td className="p-2 text-right whitespace-nowrap">
          <p className="font-semibold">{item.cantidad * item.factor_pack} und</p>
          <p className="text-gray-500">
            {formatCurrency(item.cantidad > 0 ? lineaConIva(item) / (item.cantidad * item.factor_pack) : 0)} c/u
          </p>
        </td>
        <td className="p-2">
          {item.suggested_product_id ? (
            <div>
              <p className="font-medium">{item.suggested_product_name}</p>
              <div className="flex items-center gap-1 mt-1">
                <span className="text-xs text-gray-500">{item.suggested_product_sku}</span>
                {matchBadge()}
              </div>
            </div>
          ) : (
            matchBadge()
          )}
        </td>
        <td className="p-2 text-center">
          <Button size="sm" variant="outline" onClick={() => setPicking(true)}>
            <Search className="h-3 w-3" />
          </Button>
          <Button size="sm" variant="outline" onClick={onRemove} className="ml-1 text-red-600">
            <X className="h-3 w-3" />
          </Button>
        </td>
      </tr>
      {picking && (
        <ProductPickerDialog
          query={item.descripcion}
          onPick={(p) => {
            onChange({
              ...item,
              suggested_product_id: p.id,
              suggested_product_sku: p.sku,
              suggested_product_name: p.name,
              match_reason: 'manual',
              match_score: 1,
            });
            setPicking(false);
          }}
          onClose={() => setPicking(false)}
        />
      )}
    </>
  );
}

function ProductPickerDialog({ query, onPick, onClose }: { query: string; onPick: (p: { id: string; sku: string; name: string }) => void; onClose: () => void }) {
  const [search, setSearch] = useState(query);
  const { data, isLoading } = useQuery({
    queryKey: ['products-picker', search],
    queryFn: () => productsApi.list({ q: search, page_size: 30 }),
  });

  return (
    <Dialog open onClose={onClose} title="Seleccionar producto" size="lg">
      <DialogBody>
        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar..." className="mb-3" />
        {isLoading ? <div className="text-center py-4">Buscando...</div> : (
          <div className="max-h-96 overflow-auto space-y-1">
            {data?.items.map((p) => (
              <button
                key={p.id}
                onClick={() => onPick(p)}
                className="w-full text-left p-2 hover:bg-orange-50 rounded border"
              >
                <p className="font-medium">{p.name}</p>
                <p className="text-xs text-gray-500">SKU: {p.sku}</p>
              </button>
            ))}
          </div>
        )}
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cancelar</Button>
      </DialogFooter>
    </Dialog>
  );
}

// ─── NUEVA MANUAL ─────────────────────────────────────────────────
function NuevaManualTab({ onDone }: { onDone: () => void }) {
  const qc = useQueryClient();
  const [supplierId, setSupplierId] = useState('');
  const [supplierName, setSupplierName] = useState('');
  // proveedor nuevo desde la compra manual (antes solo se podía escoger de la lista)
  const [nuevoProv, setNuevoProv] = useState(false);
  const [nuevoNit, setNuevoNit] = useState('');
  const [nuevoNombre, setNuevoNombre] = useState('');
  const [folio, setFolio] = useState('');
  const [items, setItems] = useState<EditableItem[]>([]);
  const [picking, setPicking] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<PurchasePaymentMethod>('efectivo');

  const supList = useQuery({ queryKey: ['suppliers-all'], queryFn: () => suppliersApi.list({ is_active: true, page_size: 200 }) });

  const saveMut = useMutation({
    mutationFn: async () => {
      let provId = supplierId;
      let provNombre = supplierName;
      if (nuevoProv) {
        if (!nuevoNit.trim() || !nuevoNombre.trim()) throw new Error('Escribe el NIT y el nombre del proveedor nuevo');
        const creado = await suppliersApi.create({ nit: nuevoNit.trim(), name: nuevoNombre.trim() });
        provId = creado.id;
        provNombre = creado.name;
        qc.invalidateQueries({ queryKey: ['suppliers-all'] });
      }
      return purchases.create({
      folio: folio || undefined,
      supplier_id: provId || undefined,
      supplier_name: provNombre,
      payment_method: paymentMethod,
      items: items.map((it) => ({
        product_id: it.suggested_product_id!,
        product_name: it.suggested_product_name!,
        quantity: it.cantidad,
        factor_pack: it.factor_pack,
        unit_cost: it.costo_base_unitario,
        tax_pct: it.iva_pct,
      })),
      receive_now: true,
    });
    },
    onSuccess: () => {
      toast.success('Compra registrada');
      qc.invalidateQueries({ queryKey: ['purchases'] });
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const total = items.reduce((s, it) => s + it.cantidad * it.costo_base_unitario * (1 + it.iva_pct / 100), 0);

  return (
    <div className="space-y-4">
      <Card className="p-4 grid grid-cols-4 gap-3">
        <div>
          <label className="text-sm">Proveedor</label>
          <select
            className="w-full border rounded px-3 py-2"
            value={nuevoProv ? '__nuevo__' : supplierId}
            onChange={(e) => {
              if (e.target.value === '__nuevo__') { setNuevoProv(true); setSupplierId(''); setSupplierName(''); return; }
              setNuevoProv(false);
              const s = supList.data?.items.find(x => x.id === e.target.value);
              setSupplierId(e.target.value);
              setSupplierName(s?.name || '');
            }}
          >
            <option value="">— Selecciona —</option>
            <option value="__nuevo__">+ Proveedor nuevo…</option>
            {supList.data?.items.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          {nuevoProv && (
            <div className="mt-2 space-y-2">
              <Input placeholder="NIT (sin dígito de verificación)" value={nuevoNit} onChange={(e) => setNuevoNit(e.target.value)} />
              <Input placeholder="Nombre del proveedor" value={nuevoNombre} onChange={(e) => setNuevoNombre(e.target.value)} />
              <p className="text-xs text-gray-500">Se crea al guardar la compra.</p>
            </div>
          )}
        </div>
        <div>
          <label className="text-sm">Folio</label>
          <Input value={folio} onChange={(e) => setFolio(e.target.value)} />
        </div>
        <div>
          <label className="text-sm">Medio de pago</label>
          <PaymentMethodSelect value={paymentMethod} onChange={setPaymentMethod} />
        </div>
        <div className="flex items-end">
          <Button onClick={() => setPicking(true)} className="bg-orange-500 hover:bg-orange-600 w-full">
            <Plus className="h-4 w-4 mr-1" />Agregar producto
          </Button>
        </div>
      </Card>

      <Card>
        {!items.length ? (
          <div className="p-12 text-center text-gray-500">Agrega productos a la compra</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-2">Producto</th>
                <th className="text-right p-2">Cant</th>
                <th className="text-right p-2">Costo</th>
                <th className="text-right p-2">IVA%</th>
                <th className="text-right p-2">Total</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, i) => (
                <tr key={it._id} className="border-t">
                  <td className="p-2">{it.suggested_product_name}</td>
                  <td className="p-2 text-right">
                    <Input type="number" value={it.cantidad} onChange={(e) => {
                      const v = Number(e.target.value);
                      setItems(items.map(x => x._id === it._id ? { ...x, cantidad: v } : x));
                    }} className="w-20 text-right" />
                  </td>
                  <td className="p-2 text-right">
                    <Input type="number" value={it.costo_base_unitario} onChange={(e) => {
                      const v = Number(e.target.value);
                      setItems(items.map(x => x._id === it._id ? { ...x, costo_base_unitario: v } : x));
                    }} className="w-28 text-right" />
                  </td>
                  <td className="p-2 text-right">
                    <Input type="number" value={it.iva_pct} onChange={(e) => {
                      const v = Number(e.target.value);
                      setItems(items.map(x => x._id === it._id ? { ...x, iva_pct: v } : x));
                    }} className="w-16 text-right" />
                  </td>
                  <td className="p-2 text-right font-bold">
                    {formatCurrency(it.cantidad * it.costo_base_unitario * (1 + it.iva_pct / 100))}
                  </td>
                  <td className="p-2 text-center">
                    <Button size="sm" variant="outline" onClick={() => setItems(items.filter(x => x._id !== it._id))} className="text-red-600">
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t font-bold">
                <td colSpan={4} className="p-2 text-right">Total:</td>
                <td className="p-2 text-right">{formatCurrency(total)}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        )}
      </Card>

      <div className="flex justify-end">
        <Button
          onClick={() => saveMut.mutate()}
          disabled={(!supplierName && !(nuevoProv && nuevoNit.trim() && nuevoNombre.trim())) || !items.length || saveMut.isPending}
          className="bg-green-600 hover:bg-green-700"
        >
          <Save className="h-4 w-4 mr-2" />Registrar compra
        </Button>
      </div>

      {picking && (
        <ProductPickerDialog
          query=""
          onPick={(p) => {
            setItems([...items, {
              _id: `m-${Date.now()}`,
              sku_proveedor: null,
              descripcion: p.name,
              cantidad: 1,
              costo_base_unitario: 0,
              iva_pct: 19,
              descuento: 0,
              descuento_pct: 0,
              cargos: 0,
              total_linea: 0,
              suggested_product_id: p.id,
              suggested_product_sku: p.sku,
              suggested_product_name: p.name,
              match_reason: 'manual',
              match_score: 1,
              factor_pack: 1,
              margen_pct: DEFAULT_MARGIN,
            }]);
            setPicking(false);
          }}
          onClose={() => setPicking(false)}
        />
      )}
    </div>
  );
}
