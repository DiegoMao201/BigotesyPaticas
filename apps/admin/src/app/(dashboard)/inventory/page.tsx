'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Boxes, AlertTriangle, Search, Plus, Minus, Package, History,
} from 'lucide-react';
import { toast } from 'sonner';
import { inventory, analytics, type StockRow } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Pagination } from '@/components/ui/pagination';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';

export default function InventoryPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'stock' | 'movements' | 'alerts'>('stock');
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<{ only_in_stock?: boolean; only_low_stock?: boolean }>({});
  const [adjustRow, setAdjustRow] = useState<StockRow | null>(null);

  const { data: stockData, isLoading: loadingStock } = useQuery({
    queryKey: ['inventory-stock', page, search, filter],
    queryFn: () => inventory.list({ page, page_size: 50, q: search || undefined, ...filter }),
    enabled: tab === 'stock',
  });

  const { data: alerts } = useQuery({
    queryKey: ['stock-alerts', 15],
    queryFn: () => analytics.stockAlerts(15),
    staleTime: 60_000,
  });

  const { data: movements } = useQuery({
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
      setAdjustRow(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const critical = alerts?.filter((a) => a.level === 'critical') ?? [];
  const low = alerts?.filter((a) => a.level === 'low') ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold font-display flex items-center gap-2">
          <Boxes className="w-6 h-6 text-brand-600" /> Inventario
        </h1>
        <p className="text-sm text-muted-foreground">Control de stock, ajustes y movimientos</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase">Productos</div>
          <div className="text-2xl font-bold mt-1">{stockData?.total || 0}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase">Valor inventario (costo)</div>
          <div className="text-2xl font-bold mt-1">{formatCurrency(stockData?.total_value_cost || 0)}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase">Valor venta potencial</div>
          <div className="text-2xl font-bold mt-1 text-emerald-600">{formatCurrency(stockData?.total_value_price || 0)}</div>
        </Card>
        <Card className="p-4 border-rose-200 bg-rose-50/50">
          <div className="text-xs text-rose-700 uppercase flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Sin stock</div>
          <div className="text-2xl font-bold mt-1 text-rose-700">{stockData?.out_of_stock || 0}</div>
        </Card>
      </div>

      <div className="flex gap-1 border-b border-border">
        {[
          { id: 'stock', label: 'Stock', icon: Package },
          { id: 'alerts', label: `Alertas (${critical.length + low.length})`, icon: AlertTriangle },
          { id: 'movements', label: 'Movimientos', icon: History },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id as any)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition flex items-center gap-2 ${
              tab === t.id ? 'border-brand-500 text-brand-600' : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
      </div>

      {tab === 'stock' && (
        <>
          <Card className="p-3">
            <div className="flex items-center gap-3 flex-wrap">
              <div className="relative flex-1 min-w-[240px]">
                <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                  placeholder="Buscar SKU o nombre…"
                  className="pl-9"
                />
              </div>
              <Button
                variant={filter.only_in_stock ? 'default' : 'outline'}
                size="sm"
                onClick={() => { setFilter({ only_in_stock: !filter.only_in_stock, only_low_stock: false }); setPage(1); }}
              >
                Con stock
              </Button>
              <Button
                variant={filter.only_low_stock ? 'default' : 'outline'}
                size="sm"
                onClick={() => { setFilter({ only_low_stock: !filter.only_low_stock, only_in_stock: false }); setPage(1); }}
              >
                Stock bajo
              </Button>
            </div>
          </Card>
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="text-left px-4 py-3">SKU</th>
                    <th className="text-left px-4 py-3">Producto</th>
                    <th className="text-right px-4 py-3">Stock</th>
                    <th className="text-right px-4 py-3">Reservado</th>
                    <th className="text-right px-4 py-3">Disponible</th>
                    <th className="text-right px-4 py-3">Costo</th>
                    <th className="text-right px-4 py-3">Precio</th>
                    <th className="text-right px-4 py-3">Valor (precio)</th>
                    <th className="text-right px-4 py-3">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {loadingStock ? (
                    <tr><td colSpan={9} className="text-center py-8 text-muted-foreground">Cargando…</td></tr>
                  ) : stockData?.items.length === 0 ? (
                    <tr><td colSpan={9} className="text-center py-8 text-muted-foreground">Sin productos</td></tr>
                  ) : stockData?.items.map((s) => (
                    <tr key={s.product_id} className="border-t border-border hover:bg-muted/30">
                      <td className="px-4 py-2 font-mono text-xs">{s.sku}</td>
                      <td className="px-4 py-2 max-w-xs truncate font-medium">{s.name}</td>
                      <td className="px-4 py-2 text-right">
                        <Badge variant={s.quantity <= 0 ? 'danger' : s.quantity < 5 ? 'warning' : 'success'}>
                          {s.quantity}
                        </Badge>
                      </td>
                      <td className="px-4 py-2 text-right text-muted-foreground">{s.reserved}</td>
                      <td className="px-4 py-2 text-right font-bold">{s.available}</td>
                      <td className="px-4 py-2 text-right text-muted-foreground">{formatCurrency(s.cost)}</td>
                      <td className="px-4 py-2 text-right">{formatCurrency(s.price)}</td>
                      <td className="px-4 py-2 text-right text-emerald-700 font-semibold">{formatCurrency(s.stock_value_price)}</td>
                      <td className="px-4 py-2 text-right">
                        <Button size="sm" variant="outline" onClick={() => setAdjustRow(s)}>Ajustar</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-4">
              {stockData && <Pagination page={page} pageSize={stockData.page_size} total={stockData.total} onPageChange={setPage} />}
            </div>
          </Card>
        </>
      )}

      {tab === 'alerts' && (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="text-left px-4 py-3">SKU</th>
                <th className="text-left px-4 py-3">Producto</th>
                <th className="text-right px-4 py-3">Disponible</th>
                <th className="text-left px-4 py-3">Estado</th>
              </tr>
            </thead>
            <tbody>
              {[...critical, ...low].map((a) => (
                <tr key={a.product_id} className="border-t border-border hover:bg-muted/30">
                  <td className="px-4 py-2 font-mono text-xs">{a.sku}</td>
                  <td className="px-4 py-2">{a.name}</td>
                  <td className="px-4 py-2 text-right font-bold">{a.available}</td>
                  <td className="px-4 py-2">
                    <Badge variant={a.level === 'critical' ? 'danger' : 'warning'}>
                      {a.level === 'critical' ? 'Sin stock' : 'Bajo'}
                    </Badge>
                  </td>
                </tr>
              ))}
              {(critical.length + low.length) === 0 && (
                <tr><td colSpan={4} className="text-center py-8 text-muted-foreground">Sin alertas activas</td></tr>
              )}
            </tbody>
          </table>
        </Card>
      )}

      {tab === 'movements' && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="text-left px-4 py-3">Fecha</th>
                  <th className="text-left px-4 py-3">SKU</th>
                  <th className="text-left px-4 py-3">Producto</th>
                  <th className="text-left px-4 py-3">Tipo</th>
                  <th className="text-right px-4 py-3">Δ</th>
                  <th className="text-right px-4 py-3">Después</th>
                  <th className="text-left px-4 py-3">Notas</th>
                  <th className="text-left px-4 py-3">Por</th>
                </tr>
              </thead>
              <tbody>
                {movements?.items.map((m) => (
                  <tr key={m.id} className="border-t border-border hover:bg-muted/30">
                    <td className="px-4 py-2 text-muted-foreground text-xs">{formatDate(m.occurred_at, { dateStyle: 'short', timeStyle: 'short' })}</td>
                    <td className="px-4 py-2 font-mono text-xs">{m.product_sku}</td>
                    <td className="px-4 py-2 max-w-xs truncate">{m.product_name}</td>
                    <td className="px-4 py-2"><Badge variant="info">{m.movement_type}</Badge></td>
                    <td className={`px-4 py-2 text-right font-bold ${m.quantity_delta >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {m.quantity_delta >= 0 ? '+' : ''}{m.quantity_delta}
                    </td>
                    <td className="px-4 py-2 text-right">{m.quantity_after}</td>
                    <td className="px-4 py-2 max-w-xs truncate text-muted-foreground">{m.notes || '—'}</td>
                    <td className="px-4 py-2 text-xs text-muted-foreground">{m.created_by || '—'}</td>
                  </tr>
                ))}
                {(!movements || movements.items.length === 0) && (
                  <tr><td colSpan={8} className="text-center py-8 text-muted-foreground">Sin movimientos</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Dialog open={!!adjustRow} onClose={() => setAdjustRow(null)} title="Ajuste de Inventario" description={adjustRow ? `${adjustRow.sku} · ${adjustRow.name}` : ''}>
        {adjustRow && (
          <AdjustForm
            row={adjustRow}
            onSubmit={(d) => adjustMut.mutate({ product_id: adjustRow.product_id, quantity_delta: d.delta, notes: d.notes })}
            loading={adjustMut.isPending}
          />
        )}
      </Dialog>
    </div>
  );
}

function AdjustForm({ row, onSubmit, loading }: { row: StockRow; onSubmit: (d: { delta: number; notes: string }) => void; loading: boolean }) {
  const [delta, setDelta] = useState(0);
  const [notes, setNotes] = useState('');
  const newQty = row.quantity + delta;

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit({ delta, notes }); }}>
      <DialogBody className="space-y-4">
        <div className="bg-muted/40 rounded-lg p-3 text-sm">
          <div>Stock actual: <span className="font-bold">{row.quantity}</span></div>
          <div>Nuevo stock: <span className={`font-bold ${newQty < 0 ? 'text-red-600' : ''}`}>{newQty}</span></div>
        </div>
        <div>
          <label className="text-xs font-medium mb-1 block">Cambio (+ entrada / − salida)</label>
          <div className="flex items-center gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => setDelta(delta - 1)}><Minus className="w-3 h-3" /></Button>
            <Input type="number" value={delta} onChange={(e) => setDelta(parseInt(e.target.value) || 0)} className="text-center" />
            <Button type="button" variant="outline" size="sm" onClick={() => setDelta(delta + 1)}><Plus className="w-3 h-3" /></Button>
          </div>
        </div>
        <div>
          <label className="text-xs font-medium mb-1 block">Motivo / Notas</label>
          <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Ej: Conteo físico, daño, devolución…" />
        </div>
      </DialogBody>
      <DialogFooter>
        <Button type="submit" disabled={loading || delta === 0 || newQty < 0}>
          {loading ? 'Aplicando…' : 'Aplicar ajuste'}
        </Button>
      </DialogFooter>
    </form>
  );
}
