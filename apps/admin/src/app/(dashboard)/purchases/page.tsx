'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShoppingBag, Plus, Search, RefreshCw, Truck, TrendingDown,
  ChevronRight, CheckCircle2, Clock, XCircle, Package, Trash2,
  X, DollarSign, ReceiptText, Eye,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  purchases, inventory,
  type PurchaseCreate, type PurchaseItemIn, type PurchaseOut, type PurchaseSummary,
} from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Pagination } from '@/components/ui/pagination';

// ─── Helpers ──────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, { label: string; color: string; Icon: React.ElementType }> = {
  draft: { label: 'Borrador', color: 'bg-muted text-muted-foreground', Icon: Clock },
  confirmed: { label: 'Confirmada', color: 'bg-blue-100 text-blue-700', Icon: CheckCircle2 },
  received: { label: 'Recibida', color: 'bg-emerald-100 text-emerald-700', Icon: CheckCircle2 },
  cancelled: { label: 'Cancelada', color: 'bg-rose-100 text-rose-600', Icon: XCircle },
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_LABELS[status] ?? { label: status, color: 'bg-muted text-muted-foreground', Icon: Clock };
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${s.color}`}>
      <s.Icon className="w-3 h-3" /> {s.label}
    </span>
  );
}

// ─── New Purchase Form ─────────────────────────────────────────────

interface ItemRow {
  _key: number;
  product_id: string;
  sku_interno: string;
  product_name: string;
  quantity: string;
  unit_cost: string;
  tax_pct: string;
}

const EMPTY_ITEM = (key: number): ItemRow => ({ _key: key, product_id: '', sku_interno: '', product_name: '', quantity: '1', unit_cost: '0', tax_pct: '0' });

function NewPurchaseForm({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Omit<PurchaseCreate, 'items'>>({ supplier_name: '', payment_method: 'efectivo', receive_now: true });
  const [items, setItems] = useState<ItemRow[]>([EMPTY_ITEM(0)]);
  const [keySeq, setKeySeq] = useState(1);
  const [productSearch, setProductSearch] = useState<Record<number, string>>({});

  const { data: stockData } = useQuery({
    queryKey: ['inventory-stock', 'all'],
    queryFn: () => inventory.list({ page_size: 500 }),
    staleTime: 60_000,
  });

  const createMut = useMutation({
    mutationFn: (payload: PurchaseCreate) => purchases.create(payload),
    onSuccess: (data: PurchaseOut) => {
      toast.success(`Compra ${data.folio || data.id.slice(0, 8)} creada${form.receive_now ? ' y recibida en stock' : ''}`);
      qc.invalidateQueries({ queryKey: ['purchases'] });
      qc.invalidateQueries({ queryKey: ['inventory-stock'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const subtotal = items.reduce((s, it) => {
    const qty = parseFloat(it.quantity) || 0;
    const uc = parseFloat(it.unit_cost) || 0;
    return s + qty * uc;
  }, 0);
  const taxTotal = items.reduce((s, it) => {
    const qty = parseFloat(it.quantity) || 0;
    const uc = parseFloat(it.unit_cost) || 0;
    const tax = parseFloat(it.tax_pct) || 0;
    return s + qty * uc * (tax / 100);
  }, 0);
  const total = subtotal + taxTotal;

  const updateItem = (key: number, field: keyof ItemRow, value: string) => {
    setItems((prev) => prev.map((it) => it._key === key ? { ...it, [field]: value } : it));
  };

  const selectProduct = (key: number, row: { product_id: string; sku: string; name: string; cost: number }) => {
    setItems((prev) => prev.map((it) => it._key === key ? { ...it, product_id: row.product_id, sku_interno: row.sku, product_name: row.name, unit_cost: String(row.cost) } : it));
    setProductSearch((prev) => ({ ...prev, [key]: '' }));
  };

  const submit = () => {
    if (!form.supplier_name.trim()) { toast.error('Ingresa el proveedor'); return; }
    const validItems: PurchaseItemIn[] = items
      .filter((it) => it.product_name.trim() && parseFloat(it.quantity) > 0)
      .map((it) => ({
        product_id: it.product_id || undefined,
        sku_interno: it.sku_interno || undefined,
        product_name: it.product_name,
        quantity: parseFloat(it.quantity),
        unit_cost: parseFloat(it.unit_cost) || 0,
        tax_pct: parseFloat(it.tax_pct) || 0,
      }));
    if (validItems.length === 0) { toast.error('Agrega al menos un ítem'); return; }
    createMut.mutate({ ...form, items: validItems });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-start justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl my-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold flex items-center gap-2"><ShoppingBag className="w-5 h-5 text-brand-600" /> Nueva Compra</h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted transition"><X className="w-4 h-4" /></button>
        </div>

        <div className="p-6 space-y-5">
          {/* Header fields */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase mb-1 block">Proveedor *</label>
              <Input value={form.supplier_name} onChange={(e) => setForm({ ...form, supplier_name: e.target.value })} placeholder="Nombre del proveedor" autoFocus />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase mb-1 block">Folio / Referencia</label>
              <Input value={form.folio ?? ''} onChange={(e) => setForm({ ...form, folio: e.target.value })} placeholder="FAC-001" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase mb-1 block">Método de pago</label>
              <select className="w-full h-10 border border-input rounded-md px-3 text-sm bg-background" value={form.payment_method} onChange={(e) => setForm({ ...form, payment_method: e.target.value })}>
                <option value="efectivo">Efectivo</option>
                <option value="transferencia">Transferencia</option>
                <option value="tarjeta">Tarjeta</option>
                <option value="credito">Crédito</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase mb-1 block">Fecha</label>
              <Input type="date" value={form.purchased_at ? form.purchased_at.slice(0, 10) : ''} onChange={(e) => setForm({ ...form, purchased_at: e.target.value })} />
            </div>
            <div className="sm:col-span-2">
              <label className="text-xs font-medium text-muted-foreground uppercase mb-1 block">Notas</label>
              <Input value={form.notes ?? ''} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Observaciones opcionales…" />
            </div>
          </div>

          {/* Items */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold">Productos</h3>
              <Button variant="outline" size="sm" onClick={() => { setItems((prev) => [...prev, EMPTY_ITEM(keySeq)]); setKeySeq((k) => k + 1); }}>
                <Plus className="w-3 h-3 mr-1" /> Agregar ítem
              </Button>
            </div>
            <div className="rounded-xl border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="text-left px-3 py-2">Producto</th>
                    <th className="text-right px-3 py-2 w-24">Cantidad</th>
                    <th className="text-right px-3 py-2 w-32">Costo Unit.</th>
                    <th className="text-right px-3 py-2 w-24">IVA %</th>
                    <th className="text-right px-3 py-2 w-32">Total</th>
                    <th className="w-8" />
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => {
                    const qty = parseFloat(it.quantity) || 0;
                    const uc = parseFloat(it.unit_cost) || 0;
                    const tax = parseFloat(it.tax_pct) || 0;
                    const lineTotal = qty * uc * (1 + tax / 100);
                    const search = productSearch[it._key] ?? '';
                    const suggestions = search.length >= 2
                      ? (stockData?.items ?? []).filter((p) => p.name.toLowerCase().includes(search.toLowerCase()) || p.sku.toLowerCase().includes(search.toLowerCase())).slice(0, 6)
                      : [];
                    return (
                      <tr key={it._key} className="border-t border-border">
                        <td className="px-3 py-2 relative">
                          <div className="space-y-1">
                            <Input
                              value={search || it.product_name}
                              onChange={(e) => { setProductSearch((prev) => ({ ...prev, [it._key]: e.target.value })); if (!e.target.value) updateItem(it._key, 'product_name', ''); }}
                              placeholder="Buscar o escribir producto…"
                              className="text-xs"
                            />
                            {suggestions.length > 0 && (
                              <div className="absolute z-50 bg-white border border-border rounded-lg shadow-lg w-72 max-h-48 overflow-y-auto">
                                {suggestions.map((p) => (
                                  <button key={p.product_id} className="w-full text-left px-3 py-2 text-xs hover:bg-muted/60 flex items-center justify-between" onClick={() => selectProduct(it._key, p)}>
                                    <span className="font-medium">{p.name}</span>
                                    <span className="text-muted-foreground font-mono">{p.sku}</span>
                                  </button>
                                ))}
                              </div>
                            )}
                            {it.sku_interno && <span className="text-xs text-muted-foreground font-mono">{it.sku_interno}</span>}
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          <Input type="number" min="1" value={it.quantity} onChange={(e) => updateItem(it._key, 'quantity', e.target.value)} className="text-right text-xs w-full" />
                        </td>
                        <td className="px-3 py-2">
                          <Input type="number" min="0" step="0.01" value={it.unit_cost} onChange={(e) => updateItem(it._key, 'unit_cost', e.target.value)} className="text-right text-xs w-full" />
                        </td>
                        <td className="px-3 py-2">
                          <Input type="number" min="0" max="100" value={it.tax_pct} onChange={(e) => updateItem(it._key, 'tax_pct', e.target.value)} className="text-right text-xs w-full" />
                        </td>
                        <td className="px-3 py-2 text-right font-semibold text-xs">{formatCurrency(lineTotal)}</td>
                        <td className="px-3 py-2">
                          {items.length > 1 && (
                            <button onClick={() => setItems((prev) => prev.filter((i) => i._key !== it._key))} className="p-1 rounded text-rose-500 hover:bg-rose-50 transition">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot className="bg-muted/30 text-xs border-t border-border">
                  <tr>
                    <td colSpan={4} className="px-3 py-2 text-right font-medium text-muted-foreground">Subtotal</td>
                    <td className="px-3 py-2 text-right">{formatCurrency(subtotal)}</td>
                    <td />
                  </tr>
                  <tr>
                    <td colSpan={4} className="px-3 py-2 text-right font-medium text-muted-foreground">IVA</td>
                    <td className="px-3 py-2 text-right">{formatCurrency(taxTotal)}</td>
                    <td />
                  </tr>
                  <tr className="font-bold">
                    <td colSpan={4} className="px-3 py-2 text-right text-sm">Total</td>
                    <td className="px-3 py-2 text-right text-sm text-emerald-700">{formatCurrency(total)}</td>
                    <td />
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          {/* Receive now */}
          <div className="flex items-center gap-3 p-3 bg-emerald-50 rounded-xl border border-emerald-200">
            <input type="checkbox" id="receive_now" checked={!!form.receive_now} onChange={(e) => setForm({ ...form, receive_now: e.target.checked })} className="w-4 h-4 accent-emerald-600" />
            <label htmlFor="receive_now" className="text-sm font-medium text-emerald-800">
              Recibir en inventario ahora — aplica movimientos de stock inmediatamente
            </label>
          </div>
        </div>

        <div className="flex justify-end gap-3 px-6 py-4 border-t border-border">
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={submit} disabled={createMut.isPending}>
            {createMut.isPending ? 'Guardando…' : form.receive_now ? 'Crear y recibir en stock' : 'Crear compra'}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Purchase Detail Modal ────────────────────────────────────────

function PurchaseDetail({ purchase, onClose }: { purchase: PurchaseOut; onClose: () => void }) {
  const qc = useQueryClient();
  const receiveMut = useMutation({
    mutationFn: () => purchases.receive(purchase.id),
    onSuccess: () => {
      toast.success('Compra recibida — stock actualizado');
      qc.invalidateQueries({ queryKey: ['purchases'] });
      qc.invalidateQueries({ queryKey: ['inventory-stock'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const deleteMut = useMutation({
    mutationFn: () => purchases.delete(purchase.id),
    onSuccess: () => {
      toast.success('Compra eliminada');
      qc.invalidateQueries({ queryKey: ['purchases'] });
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl my-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <h2 className="text-lg font-semibold">{purchase.folio || `Compra ${purchase.id.slice(0, 8)}`}</h2>
            <p className="text-sm text-muted-foreground">{purchase.supplier_name} · {formatDate(purchase.purchased_at)}</p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={purchase.status} />
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted transition"><X className="w-4 h-4" /></button>
          </div>
        </div>
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-muted-foreground">Pago:</span> <span className="font-medium capitalize">{purchase.payment_method}</span></div>
            {purchase.payment_reference && <div><span className="text-muted-foreground">Ref:</span> <span className="font-medium">{purchase.payment_reference}</span></div>}
            {purchase.notes && <div className="col-span-2"><span className="text-muted-foreground">Notas:</span> <span>{purchase.notes}</span></div>}
          </div>
          <table className="w-full text-sm border border-border rounded-xl overflow-hidden">
            <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="text-left px-3 py-2">Producto</th>
                <th className="text-right px-3 py-2">Cant.</th>
                <th className="text-right px-3 py-2">Costo U.</th>
                <th className="text-right px-3 py-2">IVA</th>
                <th className="text-right px-3 py-2">Total</th>
              </tr>
            </thead>
            <tbody>
              {purchase.items.map((it) => (
                <tr key={it.id} className="border-t border-border hover:bg-muted/20">
                  <td className="px-3 py-2"><div className="font-medium">{it.product_name}</div>{it.sku_interno && <div className="text-xs text-muted-foreground font-mono">{it.sku_interno}</div>}</td>
                  <td className="px-3 py-2 text-right">{it.quantity}</td>
                  <td className="px-3 py-2 text-right">{formatCurrency(it.unit_cost)}</td>
                  <td className="px-3 py-2 text-right">{it.tax_pct}%</td>
                  <td className="px-3 py-2 text-right font-semibold">{formatCurrency(it.total_cost)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-muted/30 text-sm font-bold border-t border-border">
              <tr>
                <td colSpan={4} className="px-3 py-2 text-right">Total</td>
                <td className="px-3 py-2 text-right text-emerald-700">{formatCurrency(purchase.total)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
        <div className="flex justify-between gap-3 px-6 py-4 border-t border-border">
          <div>
            {purchase.status !== 'received' && purchase.status !== 'cancelled' && (
              <Button variant="outline" onClick={() => { if (confirm('¿Eliminar esta compra?')) deleteMut.mutate(); }} disabled={deleteMut.isPending} className="text-rose-600 hover:text-rose-700 border-rose-200">
                <Trash2 className="w-4 h-4 mr-1" /> Eliminar
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>Cerrar</Button>
            {purchase.status !== 'received' && purchase.status !== 'cancelled' && (
              <Button onClick={() => receiveMut.mutate()} disabled={receiveMut.isPending}>
                <Package className="w-4 h-4 mr-1" />
                {receiveMut.isPending ? 'Recibiendo…' : 'Marcar como recibida'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────

export default function PurchasesPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['purchases', page, search, statusFilter],
    queryFn: () => purchases.list({ q: search || undefined, status: statusFilter || undefined, page, page_size: 30 }),
    staleTime: 30_000,
  });

  const { data: detailData } = useQuery({
    queryKey: ['purchase-detail', detailId],
    queryFn: () => purchases.get(detailId!),
    enabled: !!detailId,
  });

  const { data: stats } = useQuery({
    queryKey: ['purchases-stats'],
    queryFn: purchases.stats,
    staleTime: 60_000,
  });

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <ShoppingBag className="w-6 h-6 text-brand-600" /> Compras
          </h1>
          <p className="text-sm text-muted-foreground">Registro de compras a proveedores e ingreso al inventario</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => qc.invalidateQueries({ queryKey: ['purchases'] })}>
            <RefreshCw className="w-4 h-4 mr-1" /> Actualizar
          </Button>
          <Button size="sm" onClick={() => setShowForm(true)}>
            <Plus className="w-4 h-4 mr-1" /> Nueva Compra
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Card className="p-4">
          <div className="flex items-center justify-between mb-1"><span className="text-xs text-muted-foreground uppercase">Gasto del mes</span><TrendingDown className="w-4 h-4 text-rose-500" /></div>
          <div className="text-2xl font-bold font-display text-rose-600">{formatCurrency(stats?.total_spend_month ?? 0)}</div>
          <div className="text-xs text-muted-foreground mt-1">{stats?.total_count_month ?? 0} compras este mes</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between mb-1"><span className="text-xs text-muted-foreground uppercase">Total facturas</span><ReceiptText className="w-4 h-4 text-muted-foreground" /></div>
          <div className="text-2xl font-bold font-display">{data?.total ?? 0}</div>
          <div className="text-xs text-muted-foreground mt-1">En todos los estados</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between mb-1"><span className="text-xs text-muted-foreground uppercase">Top proveedor</span><Truck className="w-4 h-4 text-muted-foreground" /></div>
          <div className="text-base font-bold font-display truncate">{stats?.top_suppliers?.[0]?.supplier_name ?? '—'}</div>
          <div className="text-xs text-muted-foreground mt-1">{stats?.top_suppliers?.[0] ? formatCurrency(stats.top_suppliers[0].total) : 'Sin datos'}</div>
        </Card>
      </div>

      {/* Filters */}
      <Card className="p-3">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
            <Input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Buscar proveedor o folio…" className="pl-9" />
          </div>
          <div className="flex gap-2 flex-wrap">
            {['', 'draft', 'confirmed', 'received', 'cancelled'].map((s) => (
              <Button key={s} variant={statusFilter === s ? 'default' : 'outline'} size="sm" onClick={() => { setStatusFilter(s); setPage(1); }}>
                {s === '' ? 'Todos' : STATUS_LABELS[s]?.label ?? s}
              </Button>
            ))}
          </div>
        </div>
      </Card>

      {/* Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="text-left px-4 py-3">Folio</th>
                <th className="text-left px-4 py-3">Proveedor</th>
                <th className="text-left px-4 py-3">Fecha</th>
                <th className="text-left px-4 py-3">Estado</th>
                <th className="text-right px-4 py-3">Ítems</th>
                <th className="text-right px-4 py-3">Pago</th>
                <th className="text-right px-4 py-3">Total</th>
                <th className="text-center px-4 py-3">Ver</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? Array.from({ length: 6 }).map((_, i) => (
                <tr key={i} className="border-t border-border">
                  <td colSpan={8} className="px-4 py-3"><div className="h-4 bg-muted/40 rounded animate-pulse" /></td>
                </tr>
              )) : data?.items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-16 text-muted-foreground">
                    <ShoppingBag className="w-12 h-12 mx-auto mb-2 opacity-20" />
                    <p className="font-medium">Sin compras registradas</p>
                    <p className="text-xs mt-1">Crea tu primera compra usando el botón de arriba</p>
                  </td>
                </tr>
              ) : data?.items.map((p: PurchaseSummary) => (
                <tr key={p.id} className="border-t border-border hover:bg-muted/20 cursor-pointer" onClick={() => setDetailId(p.id)}>
                  <td className="px-4 py-3 font-mono text-xs font-medium">{p.folio || p.id.slice(0, 8)}</td>
                  <td className="px-4 py-3 font-medium">{p.supplier_name}</td>
                  <td className="px-4 py-3 text-muted-foreground text-xs whitespace-nowrap">{formatDate(p.purchased_at)}</td>
                  <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                  <td className="px-4 py-3 text-right text-muted-foreground">{p.items_count}</td>
                  <td className="px-4 py-3 text-right text-xs capitalize text-muted-foreground">{p.payment_method}</td>
                  <td className="px-4 py-3 text-right font-semibold text-emerald-700">{formatCurrency(p.total)}</td>
                  <td className="px-4 py-3 text-center">
                    <button className="p-1.5 rounded text-muted-foreground hover:text-brand-600 hover:bg-brand-50 transition" onClick={(e) => { e.stopPropagation(); setDetailId(p.id); }}>
                      <Eye className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-4 border-t border-border">
          {data && <Pagination page={page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />}
        </div>
      </Card>

      {showForm && <NewPurchaseForm onClose={() => setShowForm(false)} />}
      {detailId && detailData && <PurchaseDetail purchase={detailData} onClose={() => setDetailId(null)} />}
    </div>
  );
}
