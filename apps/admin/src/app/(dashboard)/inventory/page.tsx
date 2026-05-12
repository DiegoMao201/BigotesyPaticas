'use client';

import { useState, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Boxes, AlertTriangle, Search, Package, History, ArrowUpDown,
  ArrowUp, ArrowDown, Edit2, Check, X, RefreshCw, TrendingUp,
  DollarSign, ShoppingBag, Plus, Minus, Sparkles, Download,
} from 'lucide-react';
import { toast } from 'sonner';
import { api, inventory, analytics, type StockRow } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Pagination } from '@/components/ui/pagination';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';

type SortField = 'quantity' | 'cost' | 'price' | 'margin_pct' | 'stock_value_price' | 'stock_value_cost' | 'name';
type SortDir = 'asc' | 'desc';

interface EditingPrice {
  product_id: string;
  cost: string;
  price: string;
}

function SortTh({
  field, label, current, dir, onSort, className = '',
}: {
  field: SortField; label: string; current: SortField; dir: SortDir; onSort: (f: SortField) => void; className?: string;
}) {
  const active = current === field;
  const Icon = active ? (dir === 'asc' ? ArrowUp : ArrowDown) : ArrowUpDown;
  return (
    <th className={`px-3 py-3 cursor-pointer select-none hover:bg-muted/60 transition-colors ${className}`} onClick={() => onSort(field)}>
      <span className="flex items-center gap-1 justify-end">
        <span className={active ? 'text-brand-600 font-semibold' : ''}>{label}</span>
        <Icon className={`w-3 h-3 ${active ? 'text-brand-600' : 'text-muted-foreground/50'}`} />
      </span>
    </th>
  );
}

export default function InventoryPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'stock' | 'movements' | 'alerts' | 'analytics'>('stock');
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<{ only_in_stock?: boolean; only_low_stock?: boolean }>({});
  const [sortBy, setSortBy] = useState<SortField>('quantity');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [adjustRow, setAdjustRow] = useState<StockRow | null>(null);
  const [adjustDelta, setAdjustDelta] = useState('');
  const [adjustNotes, setAdjustNotes] = useState('');
  const [editing, setEditing] = useState<EditingPrice | null>(null);
  const editCostRef = useRef<HTMLInputElement>(null);

  const handleSort = useCallback((field: SortField) => {
    if (sortBy === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortDir('desc');
    }
    setPage(1);
  }, [sortBy]);

  const { data: stockData, isLoading: loadingStock } = useQuery({
    queryKey: ['inventory-stock', page, search, filter, sortBy, sortDir],
    queryFn: () => inventory.list({ page, page_size: 50, q: search || undefined, sort_by: sortBy, sort_dir: sortDir, ...filter }),
    enabled: tab === 'stock',
    staleTime: 30_000,
  });

  const { data: alerts } = useQuery({
    queryKey: ['stock-alerts', 15],
    queryFn: () => analytics.stockAlerts(15),
    staleTime: 60_000,
  });

  const { data: movements, isLoading: loadingMovements } = useQuery({
    queryKey: ['inventory-movements'],
    queryFn: () => inventory.movements({ limit: 200 }),
    enabled: tab === 'movements',
  });

  const adjustMut = useMutation({
    mutationFn: inventory.adjust,
    onSuccess: () => {
      toast.success('Ajuste aplicado');
      qc.invalidateQueries({ queryKey: ['inventory-stock'] });
      qc.invalidateQueries({ queryKey: ['inventory-movements'] });
      qc.invalidateQueries({ queryKey: ['stock-alerts'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      setAdjustRow(null);
      setAdjustDelta('');
      setAdjustNotes('');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const pricingMut = useMutation({
    mutationFn: ({ product_id, cost, price }: { product_id: string; cost?: number; price?: number }) =>
      api(`/v1/inventory/stock/${product_id}/pricing`, {
        method: 'PATCH',
        body: JSON.stringify({ cost, price }),
      }),
    onSuccess: () => {
      toast.success('Precios actualizados');
      qc.invalidateQueries({ queryKey: ['inventory-stock'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      setEditing(null);
    },
    onError: (e: Error) => toast.error('Error: ' + e.message),
  });

  const startEdit = (row: StockRow) => {
    setEditing({ product_id: row.product_id, cost: String(row.cost), price: String(row.price) });
    setTimeout(() => editCostRef.current?.focus(), 50);
  };

  const saveEdit = () => {
    if (!editing) return;
    const cost = parseFloat(editing.cost.replace(/[^0-9.]/g, ''));
    const price = parseFloat(editing.price.replace(/[^0-9.]/g, ''));
    if (isNaN(cost) || isNaN(price)) { toast.error('Valores inválidos'); return; }
    pricingMut.mutate({ product_id: editing.product_id, cost, price });
  };

  const critical = alerts?.filter((a) => a.level === 'critical') ?? [];
  const low = alerts?.filter((a) => a.level === 'low') ?? [];
  const totalCost = stockData?.total_value_cost ?? 0;
  const totalPrice = stockData?.total_value_price ?? 0;
  const potentialMargin = totalPrice > 0 ? ((totalPrice - totalCost) / totalPrice * 100).toFixed(1) : '0.0';
  const marginColor = (m: number) => m >= 40 ? 'text-emerald-600 font-semibold' : m >= 20 ? 'text-brand-600' : m >= 0 ? 'text-amber-600' : 'text-rose-600 font-semibold';

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <Boxes className="w-6 h-6 text-brand-600" /> Inventario
          </h1>
          <p className="text-sm text-muted-foreground">Stock, precios, márgenes y movimientos · Clic en columna para ordenar</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => qc.invalidateQueries({ queryKey: ['inventory-stock'] })}>
          <RefreshCw className="w-4 h-4 mr-1" /> Actualizar
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Card className="p-4">
          <div className="flex items-center justify-between mb-1"><span className="text-xs text-muted-foreground uppercase">Productos</span><Package className="w-4 h-4 text-muted-foreground" /></div>
          <div className="text-2xl font-bold font-display">{stockData?.total || 0}</div>
          <div className="text-xs text-muted-foreground mt-1">{stockData?.out_of_stock ?? 0} sin stock · {stockData?.low_stock ?? 0} bajo</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between mb-1"><span className="text-xs text-muted-foreground uppercase">Valor costo</span><DollarSign className="w-4 h-4 text-muted-foreground" /></div>
          <div className="text-2xl font-bold font-display">{formatCurrency(totalCost)}</div>
          <div className="text-xs text-muted-foreground mt-1">Capital invertido</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between mb-1"><span className="text-xs text-muted-foreground uppercase">Valor venta</span><ShoppingBag className="w-4 h-4 text-emerald-600" /></div>
          <div className="text-2xl font-bold font-display text-emerald-600">{formatCurrency(totalPrice)}</div>
          <div className="text-xs text-muted-foreground mt-1">Si se vende todo</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between mb-1"><span className="text-xs text-muted-foreground uppercase">Margen global</span><TrendingUp className="w-4 h-4 text-brand-600" /></div>
          <div className={`text-2xl font-bold font-display ${Number(potentialMargin) >= 30 ? 'text-emerald-600' : 'text-amber-600'}`}>{potentialMargin}%</div>
          <div className="text-xs text-muted-foreground mt-1">Margen portafolio</div>
        </Card>
      </div>

      <div className="flex gap-1 border-b border-border overflow-x-auto">
        {[{ id: 'stock', label: 'Stock & Precios', icon: Package }, { id: 'alerts', label: `Alertas (${critical.length + low.length})`, icon: AlertTriangle }, { id: 'movements', label: 'Movimientos', icon: History }, { id: 'analytics', label: 'Análisis IA', icon: Sparkles }].map((t) => (
          <button key={t.id} onClick={() => setTab(t.id as 'stock' | 'movements' | 'alerts' | 'analytics')} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${tab === t.id ? 'border-brand-500 text-brand-600' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
        <Button
          variant="outline"
          size="sm"
          className="ml-auto"
          onClick={async () => {
            try {
              const blob = await inventory.exportExcel();
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `inventario_${new Date().toISOString().slice(0, 10)}.xlsx`;
              a.click();
              URL.revokeObjectURL(url);
              toast.success('Excel descargado');
            } catch (e) {
              toast.error((e as Error).message);
            }
          }}
        >
          <Download className="w-4 h-4 mr-1" />Excel
        </Button>
      </div>

      {tab === 'stock' && (
        <>
          <Card className="p-3">
            <div className="flex items-center gap-3 flex-wrap">
              <div className="relative flex-1 min-w-[240px]">
                <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
                <Input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Buscar SKU o nombre…" className="pl-9" />
              </div>
              <div className="flex gap-2">
                <Button variant={filter.only_in_stock ? 'default' : 'outline'} size="sm" onClick={() => { setFilter({ only_in_stock: !filter.only_in_stock }); setPage(1); }}>Con stock</Button>
                <Button variant={filter.only_low_stock ? 'default' : 'outline'} size="sm" onClick={() => { setFilter({ only_low_stock: !filter.only_low_stock }); setPage(1); }}>Stock bajo</Button>
              </div>
            </div>
          </Card>

          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="text-left px-3 py-3 min-w-[80px]">SKU</th>
                    <SortTh field="name" label="Producto" current={sortBy} dir={sortDir} onSort={handleSort} className="text-left min-w-[180px]" />
                    <SortTh field="quantity" label="Stock" current={sortBy} dir={sortDir} onSort={handleSort} className="text-right" />
                    <th className="text-right px-3 py-3">Disp.</th>
                    <SortTh field="cost" label="Costo" current={sortBy} dir={sortDir} onSort={handleSort} className="text-right" />
                    <SortTh field="price" label="Precio V." current={sortBy} dir={sortDir} onSort={handleSort} className="text-right" />
                    <SortTh field="margin_pct" label="Margen" current={sortBy} dir={sortDir} onSort={handleSort} className="text-right" />
                    <SortTh field="stock_value_price" label="Val. Stock" current={sortBy} dir={sortDir} onSort={handleSort} className="text-right" />
                    <th className="text-center px-3 py-3 min-w-[90px]">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {loadingStock ? Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i} className="border-t border-border"><td colSpan={9} className="px-3 py-3"><div className="h-4 bg-muted/40 rounded animate-pulse" /></td></tr>
                  )) : stockData?.items.length === 0 ? (
                    <tr><td colSpan={9} className="text-center py-12 text-muted-foreground"><Package className="w-10 h-10 mx-auto mb-2 opacity-30" /><p>Sin productos</p></td></tr>
                  ) : stockData?.items.map((s) => {
                    const isEditing = editing?.product_id === s.product_id;
                    const liveMargin = isEditing && editing
                      ? (() => { const c = parseFloat(editing.cost) || 0; const p = parseFloat(editing.price) || 0; return p > 0 ? ((p - c) / p * 100) : 0; })()
                      : (s as any).margin_pct ?? 0;
                    return (
                      <tr key={s.product_id} className={`border-t border-border transition-colors ${isEditing ? 'bg-brand-50/60' : 'hover:bg-muted/20'}`}>
                        <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{s.sku}</td>
                        <td className="px-3 py-2 max-w-[200px]"><span className="font-medium text-sm leading-tight block truncate" title={s.name}>{s.name}</span></td>
                        <td className="px-3 py-2 text-right">
                          <Badge variant={s.quantity <= 0 ? 'danger' : s.quantity < 5 ? 'warning' : 'success'}>{s.quantity}</Badge>
                        </td>
                        <td className="px-3 py-2 text-right font-semibold">{s.available}</td>
                        <td className="px-3 py-2 text-right">
                          {isEditing ? (
                            <input ref={editCostRef} type="number" className="w-28 text-right border border-brand-400 rounded px-2 py-1 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-400" value={editing!.cost} onChange={(e) => setEditing({ ...editing!, cost: e.target.value })} onKeyDown={(e) => { if (e.key === 'Enter') saveEdit(); if (e.key === 'Escape') setEditing(null); }} />
                          ) : <span className="text-muted-foreground">{formatCurrency(s.cost)}</span>}
                        </td>
                        <td className="px-3 py-2 text-right">
                          {isEditing ? (
                            <input type="number" className="w-28 text-right border border-brand-400 rounded px-2 py-1 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-400" value={editing!.price} onChange={(e) => setEditing({ ...editing!, price: e.target.value })} onKeyDown={(e) => { if (e.key === 'Enter') saveEdit(); if (e.key === 'Escape') setEditing(null); }} />
                          ) : <span className="font-semibold">{formatCurrency(s.price)}</span>}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <span className={`text-xs ${marginColor(liveMargin)}`}>{liveMargin !== null ? `${Number(liveMargin).toFixed(1)}%` : '—'}</span>
                        </td>
                        <td className="px-3 py-2 text-right text-emerald-700 font-semibold text-xs">{formatCurrency(s.stock_value_price)}</td>
                        <td className="px-3 py-2 text-center">
                          {isEditing ? (
                            <div className="flex items-center justify-center gap-1">
                              <button onClick={saveEdit} disabled={pricingMut.isPending} className="p-1.5 rounded bg-emerald-600 text-white hover:bg-emerald-700 transition" title="Guardar"><Check className="w-3.5 h-3.5" /></button>
                              <button onClick={() => setEditing(null)} className="p-1.5 rounded bg-muted text-muted-foreground hover:bg-muted/70 transition" title="Cancelar"><X className="w-3.5 h-3.5" /></button>
                            </div>
                          ) : (
                            <div className="flex items-center justify-center gap-1">
                              <button onClick={() => startEdit(s)} className="p-1.5 rounded text-muted-foreground hover:text-brand-600 hover:bg-brand-50 transition" title="Editar precios"><Edit2 className="w-3.5 h-3.5" /></button>
                              <button onClick={() => { setAdjustRow(s); setAdjustDelta(''); setAdjustNotes(''); }} className="p-1.5 rounded text-muted-foreground hover:text-amber-600 hover:bg-amber-50 transition" title="Ajustar stock"><ArrowUpDown className="w-3.5 h-3.5" /></button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="px-4 border-t border-border">
              {stockData && <Pagination page={page} pageSize={stockData.page_size} total={stockData.total} onPageChange={setPage} />}
            </div>
          </Card>
        </>
      )}

      {tab === 'alerts' && (
        <div className="space-y-4">
          {critical.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-rose-700 flex items-center gap-2 mb-2"><AlertTriangle className="w-4 h-4" /> Sin stock ({critical.length})</h3>
              <Card className="overflow-hidden"><table className="w-full text-sm"><thead className="bg-rose-50 text-xs uppercase text-rose-700"><tr><th className="text-left px-4 py-3">SKU</th><th className="text-left px-4 py-3">Producto</th><th className="text-right px-4 py-3">Disponible</th></tr></thead><tbody>{critical.map((a) => (<tr key={a.product_id} className="border-t border-rose-100"><td className="px-4 py-2 font-mono text-xs">{a.sku}</td><td className="px-4 py-2">{a.name}</td><td className="px-4 py-2 text-right"><Badge variant="danger">{a.available}</Badge></td></tr>))}</tbody></table></Card>
            </div>
          )}
          {low.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-amber-700 flex items-center gap-2 mb-2"><AlertTriangle className="w-4 h-4" /> Stock bajo ({low.length})</h3>
              <Card className="overflow-hidden"><table className="w-full text-sm"><thead className="bg-amber-50 text-xs uppercase text-amber-700"><tr><th className="text-left px-4 py-3">SKU</th><th className="text-left px-4 py-3">Producto</th><th className="text-right px-4 py-3">Disponible</th></tr></thead><tbody>{low.map((a) => (<tr key={a.product_id} className="border-t border-amber-100"><td className="px-4 py-2 font-mono text-xs">{a.sku}</td><td className="px-4 py-2">{a.name}</td><td className="px-4 py-2 text-right"><Badge variant="warning">{a.available}</Badge></td></tr>))}</tbody></table></Card>
            </div>
          )}
          {critical.length === 0 && low.length === 0 && (
            <div className="text-center py-16 text-muted-foreground"><Package className="w-12 h-12 mx-auto mb-3 opacity-20" /><p className="font-medium">Todo el inventario está bien abastecido 🎉</p></div>
          )}
        </div>
      )}

      {tab === 'movements' && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="text-left px-4 py-3">Fecha</th>
                  <th className="text-left px-4 py-3">Producto</th>
                  <th className="text-left px-4 py-3">Tipo</th>
                  <th className="text-right px-4 py-3">Delta</th>
                  <th className="text-right px-4 py-3">Resultante</th>
                  <th className="text-left px-4 py-3">Notas</th>
                </tr>
              </thead>
              <tbody>
                {loadingMovements ? (
                  <tr><td colSpan={6} className="text-center py-8 text-muted-foreground">Cargando…</td></tr>
                ) : movements?.items.map((m) => (
                  <tr key={m.id} className="border-t border-border hover:bg-muted/20">
                    <td className="px-4 py-2 text-xs text-muted-foreground whitespace-nowrap">{formatDate(m.occurred_at)}</td>
                    <td className="px-4 py-2"><div className="font-medium text-xs">{m.product_name}</div><div className="text-xs text-muted-foreground font-mono">{m.product_sku}</div></td>
                    <td className="px-4 py-2">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${m.movement_type === 'PURCHASE' ? 'bg-emerald-100 text-emerald-700' : m.movement_type === 'SALE' ? 'bg-blue-100 text-blue-700' : m.movement_type === 'ADJUSTMENT' ? 'bg-amber-100 text-amber-700' : 'bg-muted text-muted-foreground'}`}>
                        {m.movement_type === 'PURCHASE' ? 'Compra' : m.movement_type === 'SALE' ? 'Venta' : m.movement_type === 'ADJUSTMENT' ? 'Ajuste' : m.movement_type}
                      </span>
                    </td>
                    <td className={`px-4 py-2 text-right font-semibold ${m.quantity_delta > 0 ? 'text-emerald-600' : 'text-rose-600'}`}>{m.quantity_delta > 0 ? '+' : ''}{m.quantity_delta}</td>
                    <td className="px-4 py-2 text-right text-muted-foreground">{m.quantity_after}</td>
                    <td className="px-4 py-2 text-xs text-muted-foreground max-w-xs truncate">{m.notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === 'analytics' && <AnalyticsTab />}

      {adjustRow && (
        <Dialog open onClose={() => setAdjustRow(null)}>
          <div className="p-6 space-y-4 max-w-sm">
            <h3 className="font-semibold text-lg">Ajustar Stock</h3>
            <p className="text-sm text-muted-foreground">{adjustRow.name} · <span className="font-mono">{adjustRow.sku}</span></p>
            <div className="flex items-center gap-2 p-3 bg-muted/40 rounded-lg">
              <span className="text-sm text-muted-foreground">Stock actual:</span>
              <span className="font-bold text-lg">{adjustRow.quantity}</span>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase mb-1 block">Cantidad (+ entrada / − salida)</label>
              <div className="flex items-center gap-2">
                <Button type="button" variant="outline" size="sm" onClick={() => setAdjustDelta(String((parseInt(adjustDelta) || 0) - 1))}><Minus className="w-3 h-3" /></Button>
                <Input type="number" value={adjustDelta} onChange={(e) => setAdjustDelta(e.target.value)} className="text-center" autoFocus />
                <Button type="button" variant="outline" size="sm" onClick={() => setAdjustDelta(String((parseInt(adjustDelta) || 0) + 1))}><Plus className="w-3 h-3" /></Button>
              </div>
              {adjustDelta && <p className="text-xs mt-1 text-muted-foreground">Resultado: <strong>{adjustRow.quantity + (parseInt(adjustDelta) || 0)}</strong> unidades</p>}
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase mb-1 block">Notas</label>
              <Input value={adjustNotes} onChange={(e) => setAdjustNotes(e.target.value)} placeholder="Motivo del ajuste…" />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setAdjustRow(null)}>Cancelar</Button>
              <Button onClick={() => {
                const delta = parseInt(adjustDelta);
                if (isNaN(delta) || delta === 0) return toast.error('Cantidad inválida');
                adjustMut.mutate({ product_id: adjustRow.product_id as any, quantity_delta: delta, notes: adjustNotes || undefined });
              }} disabled={adjustMut.isPending || !adjustDelta}>
                {adjustMut.isPending ? 'Aplicando…' : 'Aplicar ajuste'}
              </Button>
            </DialogFooter>
          </div>
        </Dialog>
      )}
    </div>
  );
}

function AnalyticsTab() {
  const [daysShort, setDaysShort] = useState(30);
  const [daysLong, setDaysLong] = useState(90);
  const [filter, setFilter] = useState<'all' | 'comprar' | 'agotado' | 'sobrestock'>('comprar');
  const [classFilter, setClassFilter] = useState<'all' | 'A' | 'B' | 'C'>('all');

  const { data, isLoading } = useQuery({
    queryKey: ['velocity-analysis', daysShort, daysLong],
    queryFn: () => inventory.velocityAnalysis(daysShort, daysLong),
    staleTime: 5 * 60_000,
  });

  if (isLoading) return <Card className="p-12 text-center text-muted-foreground">Calculando análisis IA…</Card>;
  if (!data) return null;

  const filtered = data.products.filter((p) => {
    if (filter === 'comprar' && !p.requiere_compra) return false;
    if (filter === 'agotado' && p.estado !== 'AGOTADO') return false;
    if (filter === 'sobrestock' && p.estado !== 'SOBRESTOCK') return false;
    if (classFilter !== 'all' && p.clase_abc !== classFilter) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card className="p-3">
          <p className="text-xs text-muted-foreground">Total productos</p>
          <p className="text-2xl font-bold">{data.summary.total_productos}</p>
        </Card>
        <Card className="p-3">
          <p className="text-xs text-muted-foreground">💀 Agotados</p>
          <p className="text-2xl font-bold text-red-600">{data.summary.agotados}</p>
        </Card>
        <Card className="p-3">
          <p className="text-xs text-muted-foreground">🛒 Requieren compra</p>
          <p className="text-2xl font-bold text-orange-600">{data.summary.requieren_compra}</p>
        </Card>
        <Card className="p-3">
          <p className="text-xs text-muted-foreground">🧊 Sobre-stock</p>
          <p className="text-2xl font-bold text-blue-600">{data.summary.sobrestock}</p>
        </Card>
        <Card className="p-3">
          <p className="text-xs text-muted-foreground">💰 Valor inventario</p>
          <p className="text-xl font-bold">{formatCurrency(data.summary.valor_inventario)}</p>
        </Card>
      </div>

      <Card className="p-4 flex flex-wrap items-center gap-3">
        <div className="text-sm font-medium">Ventana:</div>
        <select className="border rounded px-2 py-1 text-sm" value={daysShort} onChange={(e) => setDaysShort(Number(e.target.value))}>
          <option value={7}>7d corto</option>
          <option value={14}>14d corto</option>
          <option value={30}>30d corto</option>
        </select>
        <select className="border rounded px-2 py-1 text-sm" value={daysLong} onChange={(e) => setDaysLong(Number(e.target.value))}>
          <option value={30}>30d largo</option>
          <option value={60}>60d largo</option>
          <option value={90}>90d largo</option>
          <option value={180}>180d largo</option>
        </select>

        <div className="ml-4 flex gap-1">
          {(['comprar', 'agotado', 'sobrestock', 'all'] as const).map((f) => (
            <Button key={f} size="sm" variant={filter === f ? 'default' : 'outline'} onClick={() => setFilter(f)}>
              {f === 'comprar' ? '🛒 Comprar' : f === 'agotado' ? '💀 Agotados' : f === 'sobrestock' ? '🧊 Sobre-stock' : 'Todos'}
            </Button>
          ))}
        </div>
        <div className="flex gap-1">
          {(['all', 'A', 'B', 'C'] as const).map((c) => (
            <Button key={c} size="sm" variant={classFilter === c ? 'default' : 'outline'} onClick={() => setClassFilter(c)}>
              {c === 'all' ? 'ABC' : c}
            </Button>
          ))}
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="overflow-auto max-h-[600px]">
          <table className="w-full text-xs">
            <thead className="bg-muted/50 sticky top-0">
              <tr>
                <th className="text-left p-2">Producto</th>
                <th className="text-center p-2">ABC</th>
                <th className="text-right p-2">Stock</th>
                <th className="text-right p-2">V/día</th>
                <th className="text-right p-2">Días cob.</th>
                <th className="text-right p-2">Reorden</th>
                <th className="text-right p-2">Faltante</th>
                <th className="text-center p-2">Estado</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => {
                const estadoCls = p.estado === 'AGOTADO' ? 'bg-red-100 text-red-800' :
                                  p.estado === 'COMPRAR' ? 'bg-orange-100 text-orange-800' :
                                  p.estado === 'SOBRESTOCK' ? 'bg-blue-100 text-blue-800' :
                                  'bg-green-100 text-green-800';
                const estadoLabel = p.estado === 'AGOTADO' ? '💀 Agotado' :
                                    p.estado === 'COMPRAR' ? '🛒 Comprar' :
                                    p.estado === 'SOBRESTOCK' ? '🧊 Sobre-stock' : '✅ OK';
                const abcCls = p.clase_abc === 'A' ? 'bg-green-100 text-green-800' :
                               p.clase_abc === 'B' ? 'bg-yellow-100 text-yellow-800' :
                               'bg-gray-100 text-gray-800';
                return (
                  <tr key={p.product_id} className="border-t hover:bg-muted/20">
                    <td className="p-2">
                      <p className="font-medium">{p.name}</p>
                      <p className="text-muted-foreground font-mono">{p.sku}</p>
                    </td>
                    <td className="p-2 text-center">
                      <span className={`px-2 py-0.5 rounded ${abcCls}`}>{p.clase_abc}</span>
                    </td>
                    <td className="p-2 text-right font-bold">{p.stock}</td>
                    <td className="p-2 text-right">{p.velocidad_diaria.toFixed(2)}</td>
                    <td className="p-2 text-right">{p.dias_cobertura !== null ? p.dias_cobertura : '∞'}</td>
                    <td className="p-2 text-right">{p.punto_reorden.toFixed(0)}</td>
                    <td className="p-2 text-right font-bold text-orange-600">{p.faltante.toFixed(0)}</td>
                    <td className="p-2 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs ${estadoCls}`}>{estadoLabel}</span>
                    </td>
                  </tr>
                );
              })}
              {!filtered.length && (
                <tr><td colSpan={8} className="text-center p-8 text-muted-foreground">Sin resultados con los filtros aplicados</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
