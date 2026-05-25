'use client';

import { useState, useCallback, useMemo, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
} from 'recharts';
import {
  Boxes, AlertTriangle, Search, Package, History, ArrowUpDown,
  ArrowUp, ArrowDown, Edit2, Check, X, RefreshCw, TrendingUp,
  DollarSign, ShoppingBag, Plus, Minus, Sparkles, Download, ShoppingCart,
  ClipboardList, Upload, ChevronRight, Trash2, PlayCircle, Eye, FileSpreadsheet, SlidersHorizontal,
  Copy, MessageCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { api, inventory, analytics, inventoryCounts, type StockRow, type CountSessionOut, type CountSessionDetail, type UploadPreviewRow } from '@/lib/api';
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
  const [tab, setTab] = useState<'stock' | 'movements' | 'alerts' | 'analytics' | 'conteo' | 'ajustes'>('stock');
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
        {[{ id: 'stock', label: 'Stock & Precios', icon: Package }, { id: 'alerts', label: `Alertas (${critical.length + low.length})`, icon: AlertTriangle }, { id: 'movements', label: 'Movimientos', icon: History }, { id: 'analytics', label: 'Análisis IA', icon: Sparkles }, { id: 'ajustes', label: 'Ajustes', icon: SlidersHorizontal }, { id: 'conteo', label: 'Conteo Físico', icon: ClipboardList }].map((t) => (
          <button key={t.id} onClick={() => setTab(t.id as 'stock' | 'movements' | 'alerts' | 'analytics' | 'conteo' | 'ajustes')} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap ${tab === t.id ? 'border-brand-500 text-brand-600' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
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

      {tab === 'ajustes' && <AjustesTab />}

      {tab === 'conteo' && <ConteoTab />}

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
  const [supplierFilter, setSupplierFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [planDays, setPlanDays] = useState(8);
  const [subTab, setSubTab] = useState<'tabla' | 'velocidad' | 'plan'>('tabla');

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['velocity-analysis', daysShort, daysLong],
    queryFn: () => inventory.velocityAnalysis(daysShort, daysLong),
    staleTime: 5 * 60_000,
  });

  if (isLoading) return <Card className="p-12 text-center text-muted-foreground">Calculando análisis IA…</Card>;
  if (isError) {
    return (
      <Card className="p-8 text-center space-y-3">
        <p className="text-sm text-rose-600">No se pudo cargar el análisis IA: {(error as Error)?.message || 'error desconocido'}</p>
        <Button size="sm" variant="outline" onClick={() => refetch()}>Reintentar</Button>
      </Card>
    );
  }
  if (!data) return <Card className="p-8 text-center text-muted-foreground">Sin datos de análisis por ahora.</Card>;

  const supplierOptions = useMemo(() => {
    const vals = new Set<string>();
    for (const p of data.products) {
      vals.add(p.supplier_name || '__none__');
    }
    return Array.from(vals).sort((a, b) => a.localeCompare(b, 'es'));
  }, [data.products]);

  const categoryOptions = useMemo(() => {
    const vals = new Set<string>();
    for (const p of data.products) {
      vals.add(p.category_name || '__none__');
    }
    return Array.from(vals).sort((a, b) => a.localeCompare(b, 'es'));
  }, [data.products]);

  const scopedProducts = data.products.filter((p) => {
    if (classFilter !== 'all' && p.clase_abc !== classFilter) return false;
    if (supplierFilter !== 'all' && (p.supplier_name || '__none__') !== supplierFilter) return false;
    if (categoryFilter !== 'all' && (p.category_name || '__none__') !== categoryFilter) return false;
    return true;
  });

  const filtered = scopedProducts.filter((p) => {
    if (filter === 'comprar' && !p.requiere_compra) return false;
    if (filter === 'agotado' && p.estado !== 'AGOTADO') return false;
    if (filter === 'sobrestock' && p.estado !== 'SOBRESTOCK') return false;
    return true;
  });

  // Products that need purchasing for the plan
  const purchasePlan = scopedProducts
    .filter((p) => p.requiere_compra || p.estado === 'AGOTADO')
    .map((p) => ({
      ...p,
      qty_sugerida: Math.max(0, Math.ceil(p.velocidad_diaria * planDays - p.stock)),
      costo_estimado: Math.max(0, Math.ceil(p.velocidad_diaria * planDays - p.stock)) * ((p as any).costo_unitario ?? 0),
    }))
    .filter((p) => p.qty_sugerida > 0)
    .sort((a, b) => (b.clase_abc === 'A' ? 1 : 0) - (a.clase_abc === 'A' ? 1 : 0) || b.qty_sugerida - a.qty_sugerida);

  const topVelocity = [...scopedProducts]
    .sort((a, b) => b.velocidad_diaria - a.velocidad_diaria)
    .slice(0, 20);

  const totalPlanCost = purchasePlan.reduce((s, p) => s + (p.costo_estimado || 0), 0);
  const totalPlanUnits = purchasePlan.reduce((s, p) => s + p.qty_sugerida, 0);

  const purchaseOrderMessage = useMemo(() => {
    const today = new Date().toLocaleDateString('es-CO', { dateStyle: 'medium' });
    if (!purchasePlan.length) {
      return `Orden sugerida ${today}: no hay productos para recompra en horizonte de ${planDays} dias.`;
    }

    const grouped = new Map<string, typeof purchasePlan>();
    for (const row of purchasePlan) {
      const supplier = row.supplier_name || 'SIN PROVEEDOR ASIGNADO';
      if (!grouped.has(supplier)) grouped.set(supplier, []);
      grouped.get(supplier)!.push(row);
    }

    const lines: string[] = [];
    lines.push('ORDEN DE COMPRA SUGERIDA - BIGOTES Y PATICAS');
    lines.push(`Fecha: ${today}`);
    lines.push(`Horizonte de planeacion: ${planDays} dias`);
    lines.push('');

    let grandUnits = 0;
    let grandTotal = 0;
    for (const [supplier, rows] of grouped.entries()) {
      const supplierUnits = rows.reduce((acc, r) => acc + r.qty_sugerida, 0);
      const supplierTotal = rows.reduce((acc, r) => acc + (r.costo_estimado || 0), 0);
      grandUnits += supplierUnits;
      grandTotal += supplierTotal;

      lines.push(`Proveedor: ${supplier}`);
      for (const row of rows) {
        const compactSku = row.sku.length > 16
          ? `REF-${row.sku.replace(/[^A-Za-z0-9]/g, '').slice(-6).toUpperCase()}`
          : row.sku;
        lines.push(`- ${compactSku} | ${row.name} | Cant: ${row.qty_sugerida} | Vr. est.: ${formatCurrency(row.costo_estimado || 0)}`);
      }
      lines.push(`Subtotal proveedor: ${supplierUnits} und | ${formatCurrency(supplierTotal)}`);
      lines.push('');
    }

    lines.push(`TOTAL ORDEN: ${grandUnits} und | ${formatCurrency(grandTotal)}`);
    lines.push('Por favor confirmar disponibilidad, tiempos de entrega y condiciones comerciales.');
    lines.push('Gracias. Bigotes y Paticas.');
    return lines.join('\n');
  }, [purchasePlan, planDays]);

  const ESTADO_COLOR: Record<string, string> = {
    AGOTADO: '#ef4444', COMPRAR: '#f97316', SOBRESTOCK: '#3b82f6', OK: '#10b981',
  };

  return (
    <div className="space-y-4">
      {/* Summary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card className="p-3">
          <p className="text-xs text-muted-foreground">Total productos</p>
          <p className="text-2xl font-bold">{data.summary.total_productos}</p>
        </Card>
        <Card className="p-3 border-red-200">
          <p className="text-xs text-red-600">💀 Agotados</p>
          <p className="text-2xl font-bold text-red-600">{data.summary.agotados}</p>
        </Card>
        <Card className="p-3 border-orange-200">
          <p className="text-xs text-orange-600">🛒 Requieren compra</p>
          <p className="text-2xl font-bold text-orange-600">{data.summary.requieren_compra}</p>
        </Card>
        <Card className="p-3 border-blue-200">
          <p className="text-xs text-blue-600">🧊 Sobre-stock</p>
          <p className="text-2xl font-bold text-blue-600">{data.summary.sobrestock}</p>
        </Card>
        <Card className="p-3 border-emerald-200">
          <p className="text-xs text-emerald-600">💰 Valor inventario</p>
          <p className="text-xl font-bold text-emerald-700">{formatCurrency(data.summary.valor_inventario)}</p>
        </Card>
      </div>

      {/* Controls */}
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
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-xs text-muted-foreground">Proveedor</span>
          <select className="border rounded px-2 py-1 text-sm" value={supplierFilter} onChange={(e) => setSupplierFilter(e.target.value)}>
            <option value="all">Todos</option>
            {supplierOptions.map((s) => (
              <option key={s} value={s}>{s === '__none__' ? 'Sin proveedor' : s}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Categoria</span>
          <select className="border rounded px-2 py-1 text-sm" value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
            <option value="all">Todas</option>
            {categoryOptions.map((c) => (
              <option key={c} value={c}>{c === '__none__' ? 'Sin categoria' : c}</option>
            ))}
          </select>
        </div>
      </Card>

      {/* Sub-tabs */}
      <div className="flex gap-1 border-b border-border">
        {([
          { id: 'tabla', label: '📋 Tabla' },
          { id: 'velocidad', label: '⚡ Top Velocidad' },
          { id: 'plan', label: `🛒 Plan Compra (${planDays}d)` },
        ] as { id: typeof subTab; label: string }[]).map((t) => (
          <button
            key={t.id}
            onClick={() => setSubTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors
              ${subTab === t.id ? 'border-brand-500 text-brand-600' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* TABLA SUB-TAB */}
      {subTab === 'tabla' && (
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
                        <p className="text-[11px] text-muted-foreground">{p.category_name || 'Sin categoria'} · {p.supplier_name || 'Sin proveedor'}</p>
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
      )}

      {/* VELOCIDAD SUB-TAB */}
      {subTab === 'velocidad' && (
        <Card className="p-6">
          <h3 className="text-base font-bold mb-4">Top 20 Productos por Velocidad de Venta</h3>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topVelocity} layout="vertical" margin={{ left: 8 }}>
                <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fontSize: 10 }} label={{ value: 'unidades/día', position: 'insideBottomRight', fontSize: 10 }} />
                <YAxis type="category" dataKey="sku" tick={{ fontSize: 9 }} width={90} />
                <Tooltip
                  formatter={(v: number) => [`${v.toFixed(3)} u/día`, 'Velocidad']}
                  labelFormatter={(l) => topVelocity.find((p) => p.sku === l)?.name ?? l}
                />
                <Bar dataKey="velocidad_diaria" name="Velocidad" radius={[0, 6, 6, 0]}>
                  {topVelocity.map((p, i) => (
                    <Cell key={i} fill={ESTADO_COLOR[p.estado] ?? '#6b7280'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex gap-4 mt-3 text-xs flex-wrap">
            {Object.entries(ESTADO_COLOR).map(([estado, color]) => (
              <span key={estado} className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: color }} />
                {estado}
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* PLAN DE COMPRA SUB-TAB */}
      {subTab === 'plan' && (
        <div className="space-y-4">
          <Card className="p-4 flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Horizonte:</span>
              <select className="border rounded px-2 py-1 text-sm" value={planDays} onChange={(e) => setPlanDays(Number(e.target.value))}>
                <option value={8}>8 días</option>
                <option value={15}>15 días</option>
                <option value={20}>20 días</option>
              </select>
            </div>
            <div className="flex gap-4">
              <div>
                <span className="text-xs text-muted-foreground">Productos a comprar</span>
                <p className="text-xl font-bold text-orange-600">{purchasePlan.length}</p>
              </div>
              <div>
                <span className="text-xs text-muted-foreground">Unidades totales</span>
                <p className="text-xl font-bold">{totalPlanUnits.toLocaleString('es-CO')}</p>
              </div>
              <div>
                <span className="text-xs text-muted-foreground">Costo est. total</span>
                <p className="text-xl font-bold text-emerald-700">{formatCurrency(totalPlanCost)}</p>
              </div>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={async () => {
                  await navigator.clipboard.writeText(purchaseOrderMessage);
                  toast.success('Mensaje de orden copiado');
                }}
              >
                <Copy className="w-4 h-4 mr-1" /> Copiar mensaje OC
              </Button>
              <a href={`https://wa.me/?text=${encodeURIComponent(purchaseOrderMessage)}`} target="_blank" rel="noopener noreferrer">
                <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white">
                  <MessageCircle className="w-4 h-4 mr-1" /> Enviar por WhatsApp
                </Button>
              </a>
            </div>
          </Card>

          <Card className="p-4">
            <div className="text-sm font-semibold mb-2">Mensaje profesional de orden de compra</div>
            <textarea
              className="w-full min-h-[220px] rounded-md border border-border p-3 text-xs font-mono bg-background"
              value={purchaseOrderMessage}
              readOnly
            />
          </Card>

          <Card className="overflow-hidden">
            <div className="overflow-auto max-h-[580px]">
              <table className="w-full text-xs">
                <thead className="bg-muted/50 sticky top-0">
                  <tr>
                    <th className="text-left p-2">Producto</th>
                    <th className="text-center p-2">ABC</th>
                    <th className="text-right p-2">Stock actual</th>
                    <th className="text-right p-2">V/día</th>
                    <th className="text-right p-2">Días cob.</th>
                    <th className="text-right p-2 text-orange-700 font-bold">Cant. sugerida ({planDays}d)</th>
                    <th className="text-center p-2">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {purchasePlan.map((p) => {
                    const abcCls = p.clase_abc === 'A' ? 'bg-green-100 text-green-800' : p.clase_abc === 'B' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800';
                    const estadoCls = p.estado === 'AGOTADO' ? 'bg-red-100 text-red-800' : 'bg-orange-100 text-orange-800';
                    return (
                      <tr key={p.product_id} className={`border-t hover:bg-muted/20 ${p.clase_abc === 'A' ? 'bg-yellow-50/40' : ''}`}>
                        <td className="p-2">
                          <p className="font-medium">{p.name}</p>
                          <p className="text-muted-foreground font-mono">{p.sku}</p>
                          <p className="text-[11px] text-muted-foreground">{p.category_name || 'Sin categoria'} · {p.supplier_name || 'Sin proveedor'}</p>
                        </td>
                        <td className="p-2 text-center">
                          <span className={`px-2 py-0.5 rounded font-bold ${abcCls}`}>{p.clase_abc}</span>
                        </td>
                        <td className="p-2 text-right font-bold">{p.stock}</td>
                        <td className="p-2 text-right">{p.velocidad_diaria.toFixed(3)}</td>
                        <td className="p-2 text-right">
                          <span className={p.dias_cobertura !== null && p.dias_cobertura < planDays ? 'text-rose-600 font-bold' : ''}>
                            {p.dias_cobertura !== null ? p.dias_cobertura : '∞'}
                          </span>
                        </td>
                        <td className="p-2 text-right font-bold text-orange-700 text-sm">{p.qty_sugerida}</td>
                        <td className="p-2 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs ${estadoCls}`}>{p.estado}</span>
                        </td>
                      </tr>
                    );
                  })}
                  {!purchasePlan.length && (
                    <tr><td colSpan={7} className="text-center p-8 text-muted-foreground">✅ Sin productos que requieran compra en este período</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Conteo Físico Tab
// ─────────────────────────────────────────────────────────────────────────────

type ConteoView = 'list' | 'detail';

function statusLabel(status: string) {
  switch (status) {
    case 'draft': return { label: 'Borrador', className: 'bg-muted text-muted-foreground' };
    case 'in_progress': return { label: 'En progreso', className: 'bg-amber-100 text-amber-700' };
    case 'applied': return { label: 'Aplicado', className: 'bg-emerald-100 text-emerald-700' };
    case 'cancelled': return { label: 'Cancelado', className: 'bg-rose-100 text-rose-700' };
    default: return { label: status, className: 'bg-muted text-muted-foreground' };
  }
}

function ConteoTab() {
  const qc = useQueryClient();
  const [view, setView] = useState<ConteoView>('list');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [newNotes, setNewNotes] = useState('');
  const [previewRows, setPreviewRows] = useState<UploadPreviewRow[] | null>(null);
  const [previewStats, setPreviewStats] = useState<{ matched: number; not_found: number; with_difference: number; total_value_impact: number } | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: sessionsData, isLoading } = useQuery({
    queryKey: ['inventory-counts'],
    queryFn: () => inventoryCounts.list(),
    staleTime: 30_000,
  });

  const { data: detail, isLoading: loadingDetail } = useQuery({
    queryKey: ['inventory-counts', selectedId],
    queryFn: () => inventoryCounts.get(selectedId!),
    enabled: !!selectedId && view === 'detail',
    staleTime: 15_000,
  });

  const createMut = useMutation({
    mutationFn: () => inventoryCounts.create({ name: newName.trim(), notes: newNotes.trim() || undefined }),
    onSuccess: (session) => {
      toast.success(`Sesión "${session.name}" creada con ${session.items_count} productos`);
      qc.invalidateQueries({ queryKey: ['inventory-counts'] });
      setCreating(false);
      setNewName('');
      setNewNotes('');
      setSelectedId(session.id);
      setView('detail');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: inventoryCounts.delete,
    onSuccess: () => {
      toast.success('Sesión eliminada');
      qc.invalidateQueries({ queryKey: ['inventory-counts'] });
      setView('list');
      setSelectedId(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const applyMut = useMutation({
    mutationFn: inventoryCounts.apply,
    onSuccess: (res) => {
      toast.success(
        `Conteo aplicado: ${res.products_adjusted} productos ajustados · Impacto ${res.total_value_impact >= 0 ? '+' : ''}${formatCurrency(res.total_value_impact)}`
      );
      qc.invalidateQueries({ queryKey: ['inventory-counts'] });
      qc.invalidateQueries({ queryKey: ['inventory-counts', selectedId] });
      qc.invalidateQueries({ queryKey: ['inventory-stock'] });
      setPreviewRows(null);
      setPreviewStats(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const handleUpload = async (file: File) => {
    if (!selectedId) return;
    setUploading(true);
    setPreviewRows(null);
    setPreviewStats(null);
    try {
      const res = await inventoryCounts.uploadExcel(selectedId, file);
      setPreviewRows(res.rows);
      setPreviewStats({ matched: res.matched, not_found: res.not_found, with_difference: res.with_difference, total_value_impact: res.total_value_impact });
      toast.success(`Excel procesado: ${res.matched} productos encontrados, ${res.with_difference} con diferencia`);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  // ─── LIST VIEW ───────────────────────────────────────────────────────────

  if (view === 'list') {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold flex items-center gap-2"><ClipboardList className="w-5 h-5 text-brand-600" /> Conteo Físico de Inventario</h2>
            <p className="text-sm text-muted-foreground">Descarga plantilla Excel → llena cantidades → sube → aplica ajustes</p>
          </div>
          <Button onClick={() => setCreating(true)}>
            <Plus className="w-4 h-4 mr-1" /> Nueva sesión
          </Button>
        </div>

        {isLoading ? (
          <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-16 bg-muted/40 rounded animate-pulse" />)}</div>
        ) : sessionsData?.items.length === 0 ? (
          <Card className="p-12 text-center text-muted-foreground">
            <ClipboardList className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p className="font-medium">No hay sesiones de conteo</p>
            <p className="text-sm mt-1">Crea una nueva sesión para iniciar el conteo físico</p>
            <Button className="mt-4" onClick={() => setCreating(true)}><Plus className="w-4 h-4 mr-1" /> Nueva sesión</Button>
          </Card>
        ) : (
          <div className="space-y-2">
            {sessionsData?.items.map((s) => {
              const st = statusLabel(s.status);
              return (
                <Card key={s.id} className="p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-sm">{s.name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${st.className}`}>{st.label}</span>
                        {s.status === 'applied' && (
                          <span className="text-xs text-muted-foreground">por {s.applied_by} · {s.applied_at ? formatDate(s.applied_at) : ''}</span>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1 flex items-center gap-3 flex-wrap">
                        <span>{s.items_count} productos</span>
                        {s.status !== 'draft' && (
                          <>
                            <span className="text-emerald-600">+{s.total_positive_delta} sobrantes</span>
                            <span className="text-rose-600">-{s.total_negative_delta} faltantes</span>
                            <span className={s.total_value_impact >= 0 ? 'text-emerald-600 font-medium' : 'text-rose-600 font-medium'}>
                              Impacto: {s.total_value_impact >= 0 ? '+' : ''}{formatCurrency(s.total_value_impact)}
                            </span>
                          </>
                        )}
                        <span>{formatDate(s.created_at)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      {s.status === 'applied' && (
                        <Button variant="outline" size="sm" onClick={() => inventoryCounts.downloadReport(s.id)} title="Descargar reporte">
                          <FileSpreadsheet className="w-4 h-4" />
                        </Button>
                      )}
                      <Button variant="outline" size="sm" onClick={() => { setSelectedId(s.id); setView('detail'); setPreviewRows(null); setPreviewStats(null); }}>
                        <Eye className="w-4 h-4 mr-1" /> Abrir
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        {/* Create modal */}
        {creating && (
          <Dialog open onClose={() => setCreating(false)}>
            <div className="p-6 space-y-4 max-w-md">
              <h3 className="font-semibold text-lg flex items-center gap-2"><ClipboardList className="w-5 h-5" /> Nueva sesión de conteo</h3>
              <p className="text-sm text-muted-foreground">Se tomará un snapshot del stock actual de todos los productos activos.</p>
              <div>
                <label className="text-xs font-medium uppercase mb-1 block">Nombre de la sesión *</label>
                <Input
                  autoFocus
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Ej: Conteo mensual Mayo 2026"
                  onKeyDown={(e) => { if (e.key === 'Enter' && newName.trim().length >= 2) createMut.mutate(); }}
                />
              </div>
              <div>
                <label className="text-xs font-medium uppercase mb-1 block">Notas (opcional)</label>
                <Input value={newNotes} onChange={(e) => setNewNotes(e.target.value)} placeholder="Bodega principal, turno mañana…" />
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setCreating(false)}>Cancelar</Button>
                <Button onClick={() => createMut.mutate()} disabled={newName.trim().length < 2 || createMut.isPending}>
                  {createMut.isPending ? 'Creando…' : 'Crear sesión'}
                </Button>
              </DialogFooter>
            </div>
          </Dialog>
        )}
      </div>
    );
  }

  // ─── DETAIL VIEW ─────────────────────────────────────────────────────────

  const st = detail ? statusLabel(detail.status) : null;
  const canApply = detail?.status === 'in_progress' || (previewRows && detail?.status !== 'applied');
  const canDelete = detail?.status === 'draft' || detail?.status === 'in_progress';

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 flex-wrap">
        <button onClick={() => { setView('list'); setSelectedId(null); setPreviewRows(null); setPreviewStats(null); }} className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1">
          <ClipboardList className="w-4 h-4" /> Conteos
        </button>
        <ChevronRight className="w-4 h-4 text-muted-foreground" />
        <span className="text-sm font-medium">{detail?.name ?? 'Cargando…'}</span>
        {st && <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${st.className}`}>{st.label}</span>}
      </div>

      {loadingDetail && !detail ? (
        <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-10 bg-muted/40 rounded animate-pulse" />)}</div>
      ) : detail ? (
        <>
          {/* Progress bar (in_progress only) */}
          {detail.status === 'in_progress' && (
            <Card className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Progreso de conteo</span>
                <span className="text-sm font-bold text-brand-600">
                  {detail.items.filter(i => i.counted_qty !== null).length} / {detail.items.length} productos
                  {' '}({detail.items.length > 0 ? Math.round(detail.items.filter(i => i.counted_qty !== null).length / detail.items.length * 100) : 0}%)
                </span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className="bg-brand-500 h-2 rounded-full transition-all"
                  style={{ width: `${detail.items.length > 0 ? Math.round(detail.items.filter(i => i.counted_qty !== null).length / detail.items.length * 100) : 0}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Puedes subir múltiples lotes parciales — solo se ajustarán los productos con conteo registrado.
              </p>
            </Card>
          )}

          {/* Summary cards */}
          {detail.status !== 'draft' && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <Card className="p-4">
                <div className="text-xs text-muted-foreground uppercase mb-1">Contados</div>
                <div className="text-2xl font-bold">{detail.total_products_counted}</div>
              </Card>
              <Card className="p-4">
                <div className="text-xs text-muted-foreground uppercase mb-1">Con diferencia</div>
                <div className="text-2xl font-bold text-amber-600">{detail.total_with_difference}</div>
              </Card>
              <Card className="p-4">
                <div className="text-xs text-muted-foreground uppercase mb-1">Sobrantes / Faltantes</div>
                <div className="text-lg font-bold">
                  <span className="text-emerald-600">+{detail.total_positive_delta}</span>
                  {' / '}
                  <span className="text-rose-600">-{detail.total_negative_delta}</span>
                </div>
              </Card>
              <Card className="p-4">
                <div className="text-xs text-muted-foreground uppercase mb-1">Impacto valor</div>
                <div className={`text-2xl font-bold ${detail.total_value_impact >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {detail.total_value_impact >= 0 ? '+' : ''}{formatCurrency(detail.total_value_impact)}
                </div>
              </Card>
            </div>
          )}

          {/* Actions bar */}
          {detail.status !== 'applied' && (
            <Card className="p-4">
              <div className="flex items-center gap-3 flex-wrap">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">
                    {detail.status === 'draft'
                      ? '1️⃣ Descarga la plantilla → 2️⃣ Llena el conteo → 3️⃣ Sube el archivo → 4️⃣ Aplica ajustes'
                      : '✅ Conteo en progreso. Puedes subir más lotes parciales. Solo se ajustan los productos con conteo registrado.'}
                  </p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 flex-wrap">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => inventoryCounts.downloadTemplate(detail.id)}
                  >
                    <Download className="w-4 h-4 mr-1" /> Descargar plantilla
                  </Button>

                  <input
                    ref={fileRef}
                    type="file"
                    accept=".xlsx,.xls"
                    className="hidden"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) { handleUpload(f); e.target.value = ''; } }}
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fileRef.current?.click()}
                    disabled={uploading}
                  >
                    <Upload className="w-4 h-4 mr-1" />
                    {uploading ? 'Procesando…' : 'Subir conteo'}
                  </Button>

                  {canApply && (
                    <Button
                      size="sm"
                      onClick={() => {
                        if (!confirm('¿Aplicar ajustes al stock? Esta acción no se puede deshacer.')) return;
                        applyMut.mutate(detail.id);
                      }}
                      disabled={applyMut.isPending}
                      className="bg-emerald-600 hover:bg-emerald-700"
                    >
                      <PlayCircle className="w-4 h-4 mr-1" />
                      {applyMut.isPending ? 'Aplicando…' : 'Aplicar ajustes'}
                    </Button>
                  )}

                  {canDelete && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => { if (confirm('¿Eliminar esta sesión?')) deleteMut.mutate(detail.id); }}
                      disabled={deleteMut.isPending}
                      className="text-rose-600 hover:text-rose-700 border-rose-200 hover:border-rose-400"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          )}

          {detail.status === 'applied' && (
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => inventoryCounts.downloadReport(detail.id)}>
                <FileSpreadsheet className="w-4 h-4 mr-1" /> Descargar reporte
              </Button>
            </div>
          )}

          {/* Preview from upload */}
          {previewRows && previewRows.length > 0 && previewStats && (
            <Card className="overflow-hidden">
              <div className="px-4 py-3 border-b border-border bg-amber-50 flex items-center gap-3 flex-wrap">
                <span className="font-semibold text-sm text-amber-700">Vista previa de diferencias</span>
                <span className="text-xs text-muted-foreground">{previewStats.matched} encontrados · {previewStats.not_found} no encontrados · {previewStats.with_difference} con diferencia</span>
                <span className={`text-sm font-bold ml-auto ${previewStats.total_value_impact >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                  Impacto: {previewStats.total_value_impact >= 0 ? '+' : ''}{formatCurrency(previewStats.total_value_impact)}
                </span>
              </div>
              <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50 text-xs uppercase text-muted-foreground sticky top-0">
                    <tr>
                      <th className="text-left px-4 py-2">SKU</th>
                      <th className="text-left px-4 py-2">Producto</th>
                      <th className="text-right px-4 py-2">Sistema</th>
                      <th className="text-right px-4 py-2">Contado</th>
                      <th className="text-right px-4 py-2">Diferencia</th>
                      <th className="text-right px-4 py-2">Impacto $</th>
                      <th className="text-center px-4 py-2">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row, i) => (
                      <tr key={i} className={`border-t border-border ${row.status === 'surplus' ? 'bg-emerald-50/60' : row.status === 'shortage' ? 'bg-rose-50/60' : row.status === 'not_found' ? 'bg-amber-50/60' : ''}`}>
                        <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{row.sku}</td>
                        <td className="px-4 py-2 text-xs max-w-[200px] truncate">{row.product_name}</td>
                        <td className="px-4 py-2 text-right">{row.system_qty}</td>
                        <td className="px-4 py-2 text-right font-semibold">{row.counted_qty}</td>
                        <td className={`px-4 py-2 text-right font-bold ${row.delta > 0 ? 'text-emerald-700' : row.delta < 0 ? 'text-rose-700' : 'text-muted-foreground'}`}>
                          {row.delta > 0 ? '+' : ''}{row.delta}
                        </td>
                        <td className={`px-4 py-2 text-right text-xs ${row.value_impact >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                          {row.value_impact >= 0 ? '+' : ''}{formatCurrency(row.value_impact)}
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${row.status === 'ok' ? 'bg-muted text-muted-foreground' : row.status === 'surplus' ? 'bg-emerald-100 text-emerald-700' : row.status === 'shortage' ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700'}`}>
                            {row.status === 'ok' ? 'OK' : row.status === 'surplus' ? 'Sobrante' : row.status === 'shortage' ? 'Faltante' : 'No encontrado'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Full items table (applied session) */}
          {detail.status === 'applied' && detail.items.filter(i => i.counted_qty !== null).length > 0 && (
            <Card className="overflow-hidden">
              <div className="px-4 py-3 border-b border-border">
                <span className="font-semibold text-sm">Detalle del conteo aplicado ({detail.items.filter(i => i.counted_qty !== null).length} productos)</span>
              </div>
              <div className="overflow-x-auto max-h-[450px] overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50 text-xs uppercase text-muted-foreground sticky top-0">
                    <tr>
                      <th className="text-left px-4 py-2">SKU</th>
                      <th className="text-left px-4 py-2">Producto</th>
                      <th className="text-left px-4 py-2">Categoría</th>
                      <th className="text-right px-4 py-2">Sistema</th>
                      <th className="text-right px-4 py-2">Contado</th>
                      <th className="text-right px-4 py-2">Delta</th>
                      <th className="text-right px-4 py-2">Impacto $</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.items.filter(i => i.counted_qty !== null).map((item) => (
                      <tr key={item.id} className={`border-t border-border ${(item.delta ?? 0) > 0 ? 'bg-emerald-50/40' : (item.delta ?? 0) < 0 ? 'bg-rose-50/40' : ''}`}>
                        <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{item.sku}</td>
                        <td className="px-4 py-2 text-xs">{item.product_name}</td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">{item.category_name ?? '—'}</td>
                        <td className="px-4 py-2 text-right">{item.system_qty}</td>
                        <td className="px-4 py-2 text-right font-semibold">{item.counted_qty}</td>
                        <td className={`px-4 py-2 text-right font-bold text-xs ${(item.delta ?? 0) > 0 ? 'text-emerald-700' : (item.delta ?? 0) < 0 ? 'text-rose-700' : 'text-muted-foreground'}`}>
                          {(item.delta ?? 0) > 0 ? '+' : ''}{item.delta ?? 0}
                        </td>
                        <td className={`px-4 py-2 text-right text-xs ${(item.value_impact ?? 0) >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                          {(item.value_impact ?? 0) >= 0 ? '+' : ''}{formatCurrency(item.value_impact ?? 0)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* In-progress: show already-counted items when no fresh preview */}
          {detail.status === 'in_progress' && previewRows === null && detail.items.some(i => i.counted_qty !== null) && (
            <Card className="overflow-hidden">
              <div className="px-4 py-3 border-b border-border flex items-center gap-2">
                <span className="font-semibold text-sm">Productos ya contados en esta sesión</span>
                <span className="text-xs text-muted-foreground">{detail.items.filter(i => i.counted_qty !== null).length} de {detail.items.length}</span>
              </div>
              <div className="overflow-x-auto max-h-[350px] overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50 text-xs uppercase text-muted-foreground sticky top-0">
                    <tr>
                      <th className="text-left px-4 py-2">SKU</th>
                      <th className="text-left px-4 py-2">Producto</th>
                      <th className="text-left px-4 py-2">Categoría</th>
                      <th className="text-right px-4 py-2">Sistema</th>
                      <th className="text-right px-4 py-2">Contado</th>
                      <th className="text-right px-4 py-2">Diferencia</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.items.filter(i => i.counted_qty !== null).sort((a, b) => (a.category_name ?? '').localeCompare(b.category_name ?? '') || a.product_name.localeCompare(b.product_name)).map((item) => (
                      <tr key={item.id} className={`border-t border-border ${(item.delta ?? 0) > 0 ? 'bg-emerald-50/40' : (item.delta ?? 0) < 0 ? 'bg-rose-50/40' : ''}`}>
                        <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{item.sku}</td>
                        <td className="px-4 py-2 text-xs">{item.product_name}</td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">{item.category_name ?? '—'}</td>
                        <td className="px-4 py-2 text-right text-muted-foreground">{item.system_qty}</td>
                        <td className="px-4 py-2 text-right font-semibold">{item.counted_qty}</td>
                        <td className={`px-4 py-2 text-right font-bold text-xs ${(item.delta ?? 0) > 0 ? 'text-emerald-700' : (item.delta ?? 0) < 0 ? 'text-rose-700' : 'text-muted-foreground'}`}>
                          {(item.delta ?? 0) > 0 ? '+' : ''}{item.delta ?? 0}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Draft: show product snapshot */}
          {detail.status === 'draft' && previewRows === null && (
            <Card className="overflow-hidden">
              <div className="px-4 py-3 border-b border-border">
                <span className="font-semibold text-sm">Snapshot de productos ({detail.items.length})</span>
                <span className="text-xs text-muted-foreground ml-2">Descarga la plantilla para ver con formato Excel</span>
              </div>
              <div className="overflow-x-auto max-h-[350px] overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50 text-xs uppercase text-muted-foreground sticky top-0">
                    <tr>
                      <th className="text-left px-4 py-2">SKU</th>
                      <th className="text-left px-4 py-2">Producto</th>
                      <th className="text-left px-4 py-2">Categoría</th>
                      <th className="text-right px-4 py-2">Stock al momento</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.items.map((item) => (
                      <tr key={item.id} className="border-t border-border hover:bg-muted/20">
                        <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{item.sku}</td>
                        <td className="px-4 py-2 text-xs">{item.product_name}</td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">{item.category_name ?? '—'}</td>
                        <td className="px-4 py-2 text-right font-semibold">{item.system_qty}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      ) : null}
    </div>
  );
}

function AjustesTab() {
  const qc = useQueryClient();
  const [searchQ, setSearchQ] = useState('');
  const [selected, setSelected] = useState<StockRow | null>(null);
  const [delta, setDelta] = useState('');
  const [notes, setNotes] = useState('');

  const { data: searchData, isLoading: searching } = useQuery({
    queryKey: ['inventory-search-ajuste', searchQ],
    queryFn: () => inventory.list({ q: searchQ || undefined, page_size: 10, page: 1 }),
    enabled: searchQ.length >= 2,
    staleTime: 10_000,
  });

  const { data: adjHistory, isLoading: loadingHistory } = useQuery({
    queryKey: ['inventory-adjustments'],
    queryFn: () => inventory.movements({ movement_type: 'ADJUSTMENT', limit: 100 }),
    staleTime: 30_000,
  });

  const adjustMut = useMutation({
    mutationFn: inventory.adjust,
    onSuccess: () => {
      toast.success('Ajuste guardado');
      qc.invalidateQueries({ queryKey: ['inventory-stock'] });
      qc.invalidateQueries({ queryKey: ['inventory-movements'] });
      qc.invalidateQueries({ queryKey: ['inventory-adjustments'] });
      qc.invalidateQueries({ queryKey: ['stock-alerts'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      setDelta('');
      setNotes('');
      setSelected(null);
      setSearchQ('');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deltaNum = parseInt(delta) || 0;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Form */}
        <Card className="p-5 space-y-4">
          <div>
            <h2 className="font-semibold text-base flex items-center gap-2">
              <SlidersHorizontal className="w-5 h-5 text-brand-600" /> Ajuste rápido de stock
            </h2>
            <p className="text-sm text-muted-foreground mt-1">Busca el producto, ingresa la cantidad y guarda. Queda registrado en el historial.</p>
          </div>

          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
            <Input
              value={searchQ}
              onChange={(e) => { setSearchQ(e.target.value); setSelected(null); }}
              placeholder="Buscar por SKU o nombre…"
              className="pl-9"
            />
          </div>

          {searchQ.length >= 2 && !selected && (
            <div className="border border-border rounded-lg overflow-hidden shadow-sm">
              {searching ? (
                <div className="p-3 text-sm text-muted-foreground text-center">Buscando…</div>
              ) : (searchData?.items.length ?? 0) === 0 ? (
                <div className="p-3 text-sm text-muted-foreground text-center">Sin resultados para "{searchQ}"</div>
              ) : (
                <div className="max-h-52 overflow-y-auto divide-y divide-border">
                  {searchData?.items.map((s) => (
                    <button
                      key={s.product_id}
                      className="w-full text-left px-4 py-2.5 hover:bg-muted/40 transition-colors flex items-center justify-between gap-2"
                      onClick={() => { setSelected(s); setSearchQ(s.name); }}
                    >
                      <div>
                        <div className="text-sm font-medium">{s.name}</div>
                        <div className="text-xs text-muted-foreground font-mono">{s.sku}</div>
                      </div>
                      <Badge variant={s.quantity <= 0 ? 'danger' : s.quantity < 5 ? 'warning' : 'success'}>{s.quantity}</Badge>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {selected && (
            <div className="bg-muted/40 rounded-lg p-3 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="font-medium text-sm truncate">{selected.name}</div>
                <div className="text-xs text-muted-foreground font-mono">{selected.sku}</div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <div className="text-right">
                  <div className="text-xs text-muted-foreground">Stock actual</div>
                  <div className="font-bold text-xl">{selected.quantity}</div>
                </div>
                <button onClick={() => { setSelected(null); setSearchQ(''); setDelta(''); }} className="p-1 text-muted-foreground hover:text-foreground">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {selected && (
            <>
              <div>
                <label className="text-xs font-medium text-muted-foreground uppercase mb-1.5 block">Cantidad (+ entrada / − salida)</label>
                <div className="flex items-center gap-2">
                  <Button type="button" variant="outline" size="sm" onClick={() => setDelta(String(deltaNum - 1))}><Minus className="w-3 h-3" /></Button>
                  <Input type="number" value={delta} onChange={(e) => setDelta(e.target.value)} className="text-center" autoFocus placeholder="0" />
                  <Button type="button" variant="outline" size="sm" onClick={() => setDelta(String(deltaNum + 1))}><Plus className="w-3 h-3" /></Button>
                </div>
                {deltaNum !== 0 && (
                  <p className="text-xs mt-1.5 text-muted-foreground">
                    Stock resultante: <strong className={deltaNum > 0 ? 'text-emerald-600' : 'text-rose-600'}>{selected.quantity + deltaNum}</strong> unidades
                    <span className={`ml-1 ${deltaNum > 0 ? 'text-emerald-600' : 'text-rose-600'}`}>({deltaNum > 0 ? '+' : ''}{deltaNum})</span>
                  </p>
                )}
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground uppercase mb-1.5 block">Motivo / Notas</label>
                <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Ej: Merma, devolución, corrección…" />
              </div>
              <Button
                className="w-full"
                onClick={() => {
                  if (!deltaNum) return toast.error('La cantidad no puede ser cero');
                  adjustMut.mutate({ product_id: selected.product_id as any, quantity_delta: deltaNum, notes: notes || undefined });
                }}
                disabled={adjustMut.isPending || !deltaNum}
              >
                {adjustMut.isPending ? 'Guardando…' : 'Guardar ajuste'}
              </Button>
            </>
          )}

          {!selected && searchQ.length < 2 && (
            <div className="text-center py-8 text-muted-foreground">
              <SlidersHorizontal className="w-10 h-10 mx-auto mb-2 opacity-20" />
              <p className="text-sm">Escribe al menos 2 caracteres para buscar un producto</p>
            </div>
          )}
        </Card>

        {/* Stats */}
        <Card className="p-5">
          <h3 className="font-semibold text-sm mb-3 flex items-center gap-2"><History className="w-4 h-4 text-brand-600" /> Resumen de ajustes</h3>
          {loadingHistory ? (
            <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-10 bg-muted/40 rounded animate-pulse" />)}</div>
          ) : (() => {
            const items = adjHistory?.items ?? [];
            const entradas = items.filter(m => m.quantity_delta > 0);
            const salidas = items.filter(m => m.quantity_delta < 0);
            const totalEntrada = entradas.reduce((s, m) => s + m.quantity_delta, 0);
            const totalSalida = salidas.reduce((s, m) => s + m.quantity_delta, 0);
            return (
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-emerald-50 rounded-lg">
                  <span className="text-sm text-emerald-700">Entradas (+)</span>
                  <span className="font-bold text-emerald-700">+{totalEntrada} uds · {entradas.length} ajustes</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-rose-50 rounded-lg">
                  <span className="text-sm text-rose-700">Salidas (−)</span>
                  <span className="font-bold text-rose-700">{totalSalida} uds · {salidas.length} ajustes</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-muted/40 rounded-lg">
                  <span className="text-sm text-muted-foreground">Total registrados</span>
                  <span className="font-bold">{items.length} movimientos</span>
                </div>
              </div>
            );
          })()}
        </Card>
      </div>

      {/* History table */}
      <Card className="overflow-hidden">
        <div className="px-4 py-3 border-b border-border flex items-center gap-3">
          <span className="font-semibold text-sm">Historial de ajustes</span>
          <span className="text-xs text-muted-foreground">Últimos 100 ajustes manuales</span>
          <Button variant="outline" size="sm" className="ml-auto" onClick={() => qc.invalidateQueries({ queryKey: ['inventory-adjustments'] })}>
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="text-left px-4 py-3">Fecha</th>
                <th className="text-left px-4 py-3">Producto</th>
                <th className="text-right px-4 py-3">Delta</th>
                <th className="text-right px-4 py-3">Stock resultante</th>
                <th className="text-left px-4 py-3">Notas</th>
                <th className="text-left px-4 py-3">Usuario</th>
              </tr>
            </thead>
            <tbody>
              {loadingHistory ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-t border-border">
                    <td colSpan={6}><div className="h-8 bg-muted/40 animate-pulse mx-4 my-2 rounded" /></td>
                  </tr>
                ))
              ) : (adjHistory?.items.length ?? 0) === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-muted-foreground">
                    <SlidersHorizontal className="w-10 h-10 mx-auto mb-2 opacity-20" />
                    <p className="text-sm">No hay ajustes registrados aún</p>
                  </td>
                </tr>
              ) : adjHistory?.items.map((m) => (
                <tr key={m.id} className={`border-t border-border hover:bg-muted/20 ${m.quantity_delta > 0 ? 'bg-emerald-50/30' : 'bg-rose-50/30'}`}>
                  <td className="px-4 py-2 text-xs text-muted-foreground whitespace-nowrap">{formatDate(m.occurred_at)}</td>
                  <td className="px-4 py-2">
                    <div className="font-medium text-xs">{m.product_name}</div>
                    <div className="text-xs text-muted-foreground font-mono">{m.product_sku}</div>
                  </td>
                  <td className={`px-4 py-2 text-right font-bold text-sm ${m.quantity_delta > 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {m.quantity_delta > 0 ? '+' : ''}{m.quantity_delta}
                  </td>
                  <td className="px-4 py-2 text-right text-muted-foreground">{m.quantity_after}</td>
                  <td className="px-4 py-2 text-xs text-muted-foreground max-w-xs truncate">{m.notes ?? '—'}</td>
                  <td className="px-4 py-2 text-xs text-muted-foreground">{m.created_by ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

