'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileText, XCircle, ShoppingCart, Search, RefreshCw, Eye,
  TrendingUp, DollarSign, Hash, MessageCircle, AlertTriangle,
} from 'lucide-react';
import { toast } from 'sonner';
import { sales, adminEtl, API_BASE, type Order, type OrdersListResponse } from '@/lib/api';
import { useAuth } from '@/lib/auth-store';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Pagination } from '@/components/ui/pagination';
import { formatCurrency, formatDate } from '@/lib/utils';

const STATUS_BADGE: Record<string, 'success' | 'warning' | 'danger' | 'neutral'> = {
  Pagado: 'success',
  'Abono parcial': 'warning',
  Pendiente: 'danger',
};

function buildWhatsAppMsg(order: Order): string {
  const items = order.items.map((i) =>
    `  • ${i.name_snapshot} ×${i.quantity} → $${Number(i.line_total).toLocaleString('es-CO')}`
  ).join('\n');
  return encodeURIComponent(
    `🐾 *¡Gracias por tu compra en Bigotes y Paticas!* 🐾\n\n` +
    `📋 *Orden:* ${order.order_number}\n` +
    `📅 *Fecha:* ${new Date(order.occurred_at).toLocaleDateString('es-CO', { dateStyle: 'medium' })}\n\n` +
    `🛍️ *Productos:*\n${items}\n\n` +
    `💰 *Total:* *$${Number(order.grand_total).toLocaleString('es-CO')}*\n\n` +
    `📱 *¿Ya conocés nuestro portal?* Llevá el historial de tu mascota, acumulá Puntos Bigotes y pedí domicilio:\n` +
    `👉 https://mi.bigotesypaticas.com/registro\n\n` +
    `🛒 bigotesypaticas.com · 📸 @bigotesypaticas\n` +
    `📍 Mall Zamara Plaza, Local 2 · 320 687 6633\n\n` +
    `¡Gracias por confiar en nosotros! 🐶🐱🐾`
  );
}

function OrderDetailModal({ order, onClose, onCancelDone, onPaymentDone }: { order: Order; onClose: () => void; onCancelDone: () => void; onPaymentDone: () => void }) {
  const token = useAuth((s) => s.token);
  const qc = useQueryClient();
  const [cancelReason, setCancelReason] = useState('');
  const [showCancel, setShowCancel] = useState(false);

  const cancelMut = useMutation({
    mutationFn: () => sales.cancel(order.id, cancelReason),
    onSuccess: () => {
      toast.success('Venta anulada — stock revertido');
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['pos-history'] });
      qc.invalidateQueries({ queryKey: ['inventory-stock'] });
      onCancelDone();
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const markPaidMut = useMutation({
    mutationFn: () => sales.markPaid(order.id, { method: order.payment_method || 'Efectivo', notes: 'Marcada como pagada desde Admin' }),
    onSuccess: (res) => {
      toast.success(`Pago aplicado: ${formatCurrency(res.amount_applied)}`);
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['pos-history'] });
      qc.invalidateQueries({ queryKey: ['cash-closing-today'] });
      qc.invalidateQueries({ queryKey: ['cash-closings'] });
      onPaymentDone();
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function downloadInvoice() {
    fetch(`${API_BASE}/v1/sales/orders/${order.id}/invoice`, {
      headers: { Authorization: `Bearer ${token ?? ''}` },
    })
      .then((r) => { if (!r.ok) throw new Error('Error'); return r.blob(); })
      .then((blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `comprobante-${order.order_number}.html`;
        a.click();
        toast.success('Comprobante descargado');
      })
      .catch(() => toast.error('No se pudo generar el comprobante'));
  }

  const waText = buildWhatsAppMsg(order);

  if (showCancel) {
    return (
      <Dialog open onClose={() => setShowCancel(false)} title="Anular venta" size="sm">
        <DialogBody className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Se anulará la orden <strong>{order.order_number}</strong> y el stock será revertido automáticamente.
            Esta acción no se puede deshacer.
          </p>
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase mb-1 block">Motivo (opcional)</label>
            <Input value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} placeholder="Ej: error en la venta, devolución del cliente…" />
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowCancel(false)}>Volver</Button>
          <Button variant="destructive" disabled={cancelMut.isPending} onClick={() => cancelMut.mutate()}>
            {cancelMut.isPending ? 'Anulando…' : 'Confirmar anulación'}
          </Button>
        </DialogFooter>
      </Dialog>
    );
  }

  return (
    <Dialog open onClose={onClose} title={order.order_number} size="md">
      <DialogBody className="space-y-4">
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div><span className="text-muted-foreground">Canal:</span> <span className="font-medium">{order.channel}</span></div>
          <div><span className="text-muted-foreground">Fecha:</span> <span className="font-medium">{formatDate(order.occurred_at)}</span></div>
          <div className="flex items-center gap-1">
            <span className="text-muted-foreground">Pago:</span>
            <Badge variant={STATUS_BADGE[order.payment_status] ?? 'neutral'} className="ml-1">{order.payment_status}</Badge>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-muted-foreground">Estado:</span>
            <Badge variant={order.status === 'cancelled' ? 'danger' : 'success'} className="ml-1">{order.status}</Badge>
          </div>
          {order.notes && <div className="col-span-2 text-muted-foreground">📝 {order.notes}</div>}
        </div>

        <table className="w-full text-sm rounded-xl border border-border overflow-hidden">
          <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="text-left px-3 py-2">Producto</th>
              <th className="text-right px-3 py-2">Cant.</th>
              <th className="text-right px-3 py-2">Precio</th>
              <th className="text-right px-3 py-2">Dto.</th>
              <th className="text-right px-3 py-2">Total</th>
            </tr>
          </thead>
          <tbody>
            {order.items.map((it) => (
              <tr key={it.id} className="border-t border-border">
                <td className="px-3 py-2">
                  <div className="font-medium">{it.name_snapshot}</div>
                  <div className="text-xs text-muted-foreground font-mono">{it.sku_snapshot}</div>
                </td>
                <td className="px-3 py-2 text-right">{it.quantity}</td>
                <td className="px-3 py-2 text-right">{formatCurrency(Number(it.unit_price))}</td>
                <td className="px-3 py-2 text-right text-rose-500">{Number(it.discount) > 0 ? `-${formatCurrency(Number(it.discount))}` : '—'}</td>
                <td className="px-3 py-2 text-right font-semibold">{formatCurrency(Number(it.line_total))}</td>
              </tr>
            ))}
          </tbody>
          <tfoot className="bg-muted/30 border-t-2 border-border text-sm font-bold">
            {Number(order.discount_total) > 0 && (
              <tr><td colSpan={4} className="px-3 py-1 text-right text-rose-500 font-normal text-xs">Descuentos</td><td className="px-3 py-1 text-right text-rose-500">-{formatCurrency(Number(order.discount_total))}</td></tr>
            )}
            <tr><td colSpan={4} className="px-3 py-2 text-right">Total</td><td className="px-3 py-2 text-right text-emerald-700 text-base">{formatCurrency(Number(order.grand_total))}</td></tr>
          </tfoot>
        </table>

        {order.payments.length > 0 && (
          <div className="text-sm">
            <p className="text-xs font-medium text-muted-foreground uppercase mb-1">Pagos recibidos</p>
            {order.payments.map((p) => (
              <div key={p.id} className="flex justify-between py-0.5">
                <span className="text-muted-foreground">{p.method}</span>
                <span className="font-semibold text-emerald-600">{formatCurrency(Number(p.amount))}</span>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-2 flex-wrap pt-1">
          <Button variant="outline" size="sm" onClick={downloadInvoice}>
            <FileText className="w-4 h-4 mr-1" /> Comprobante PDF
          </Button>
          <a href={`https://wa.me/?text=${waText}`} target="_blank" rel="noopener noreferrer">
            <Button variant="outline" size="sm" className="text-emerald-700 border-emerald-300 hover:bg-emerald-50">
              <MessageCircle className="w-4 h-4 mr-1" /> WhatsApp
            </Button>
          </a>
        </div>
      </DialogBody>
      <DialogFooter>
        <div className="flex justify-between w-full">
          <div>
            {order.status !== 'cancelled' && order.payment_status !== 'Pagado' && (
              <Button
                variant="outline"
                size="sm"
                disabled={markPaidMut.isPending}
                onClick={() => markPaidMut.mutate()}
                className="text-emerald-700 border-emerald-300 hover:bg-emerald-50 mr-2"
              >
                {markPaidMut.isPending ? 'Aplicando pago…' : 'Marcar como pagada'}
              </Button>
            )}
            {order.status !== 'cancelled' && (
              <Button variant="outline" size="sm" onClick={() => setShowCancel(true)} className="text-rose-600 border-rose-200 hover:bg-rose-50">
                <XCircle className="w-4 h-4 mr-1" /> Anular venta
              </Button>
            )}
          </div>
          <Button variant="outline" onClick={onClose}>Cerrar</Button>
        </div>
      </DialogFooter>
    </Dialog>
  );
}

export default function SalesPage() {
  const qc = useQueryClient();
  const [showDateWarning, setShowDateWarning] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [paymentFilter, setPaymentFilter] = useState('');
  const [channelFilter, setChannelFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [detailOrder, setDetailOrder] = useState<Order | null>(null);

  const fixDatesMut = useMutation({
    mutationFn: () => adminEtl.fixSalesDates(false),
    onSuccess: (res) => {
      toast.success(`Fechas corregidas: ${res.updated} órdenes actualizadas`);
      qc.invalidateQueries({ queryKey: ['orders'] });
      setShowDateWarning(false);
    },
    onError: (e: Error) => toast.error(`Error: ${e.message}`),
  });

  const { data, isLoading } = useQuery<OrdersListResponse>({
    queryKey: ['orders', page, search, statusFilter, paymentFilter, channelFilter, dateFrom, dateTo],
    queryFn: () => sales.list({
      page, page_size: 30,
      q: search || undefined,
      status: statusFilter || undefined,
      payment_status: paymentFilter || undefined,
      channel: channelFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }),
    staleTime: 15_000,
  });

  const totalRevenue = data?.total_revenue ?? 0;
  const avgTicket = data?.avg_ticket ?? 0;

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <ShoppingCart className="w-6 h-6 text-brand-600" /> Ventas
          </h1>
          <p className="text-sm text-muted-foreground">Historial completo · todos los canales · clic en fila para ver detalle</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => qc.invalidateQueries({ queryKey: ['orders'] })}>
          <RefreshCw className="w-4 h-4 mr-1" /> Actualizar
        </Button>
      </div>

      {/* Date warning banner */}
      {showDateWarning && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-amber-800">Ventas legadas con fecha incorrecta (2026-05-10)</p>
              <p className="text-xs text-amber-700 mt-0.5">
                Las ventas legadas tienen la fecha de importación en lugar de la fecha real de venta.
                Haz clic en "Corregir fechas" para restaurarlas automáticamente.
              </p>
            </div>
          </div>
          <div className="flex gap-2 shrink-0">
            <Button
              size="sm"
              variant="outline"
              className="border-amber-400 text-amber-800 hover:bg-amber-100"
              onClick={() => fixDatesMut.mutate()}
              disabled={fixDatesMut.isPending}
            >
              {fixDatesMut.isPending ? 'Corrigiendo…' : 'Corregir fechas'}
            </Button>
            <button onClick={() => setShowDateWarning(false)} className="text-amber-500 hover:text-amber-700">
              <XCircle className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Card className="p-4">
          <div className="flex items-center justify-between mb-1"><span className="text-xs text-muted-foreground uppercase">Total Ventas</span><DollarSign className="w-4 h-4 text-emerald-600" /></div>
          <div className="text-2xl font-bold font-display text-emerald-600">{formatCurrency(totalRevenue)}</div>
          <div className="text-xs text-muted-foreground mt-1">{data?.active_count ?? '…'} ventas activas</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between mb-1"><span className="text-xs text-muted-foreground uppercase">Ticket promedio</span><TrendingUp className="w-4 h-4 text-brand-600" /></div>
          <div className="text-2xl font-bold font-display">{formatCurrency(avgTicket)}</div>
          <div className="text-xs text-muted-foreground mt-1">Con filtros actuales</div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between mb-1"><span className="text-xs text-muted-foreground uppercase">Órdenes</span><Hash className="w-4 h-4 text-muted-foreground" /></div>
          <div className="text-2xl font-bold font-display">{data?.total ?? '…'}</div>
          <div className="text-xs text-muted-foreground mt-1">Con filtros actuales</div>
        </Card>
      </div>

      {/* Filters */}
      <Card className="p-3 space-y-3">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="absolute left-3 top-3 w-4 h-4 text-muted-foreground" />
            <Input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Buscar por # orden…" className="pl-9" />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-muted-foreground">Desde</label>
            <Input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} className="w-40" />
            <label className="text-xs text-muted-foreground">Hasta</label>
            <Input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} className="w-40" />
            {(dateFrom || dateTo) && (
              <Button size="sm" variant="outline" onClick={() => { setDateFrom(''); setDateTo(''); setPage(1); }}>
                <XCircle className="w-3 h-3" />
              </Button>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex gap-2 flex-wrap">
            <span className="text-xs font-medium text-muted-foreground self-center">Estado:</span>
            {['', 'confirmed', 'completed', 'cancelled'].map((s) => (
              <Button key={s} variant={statusFilter === s ? 'default' : 'outline'} size="sm" onClick={() => { setStatusFilter(s); setPage(1); }}>
                {s === '' ? 'Todos' : s === 'confirmed' ? 'Confirmada' : s === 'completed' ? 'Completada' : 'Anulada'}
              </Button>
            ))}
          </div>
          <div className="flex gap-2">
            <span className="text-xs font-medium text-muted-foreground self-center">Pago:</span>
            {['', 'Pagado', 'Pendiente', 'Abono parcial'].map((s) => (
              <Button key={s} variant={paymentFilter === s ? 'default' : 'outline'} size="sm" onClick={() => { setPaymentFilter(s); setPage(1); }}>
                {s === '' ? 'Todos' : s}
              </Button>
            ))}
          </div>
          <div className="flex gap-2">
            <span className="text-xs font-medium text-muted-foreground self-center">Canal:</span>
            {['', 'POS', 'STORE', 'STORE_LEGACY', 'PORTAL'].map((s) => (
              <Button key={s} variant={channelFilter === s ? 'default' : 'outline'} size="sm" onClick={() => { setChannelFilter(s); setPage(1); }}>
                {s === '' ? 'Todos' : s}
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
                <th className="text-left px-4 py-3">Orden</th>
                <th className="text-left px-4 py-3 hidden sm:table-cell">Canal</th>
                <th className="text-left px-4 py-3">Fecha</th>
                <th className="text-right px-4 py-3">Total</th>
                <th className="text-right px-4 py-3 hidden md:table-cell">Saldo</th>
                <th className="text-center px-4 py-3">Pago</th>
                <th className="text-center px-4 py-3">Estado</th>
                <th className="text-center px-4 py-3">Ver</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="border-t border-border"><td colSpan={8} className="px-4 py-3"><div className="h-4 bg-muted/40 rounded animate-pulse" /></td></tr>
              )) : data?.items.length === 0 ? (
                <tr><td colSpan={8} className="text-center py-16 text-muted-foreground">
                  <ShoppingCart className="w-12 h-12 mx-auto mb-2 opacity-20" />
                  <p>No hay ventas con los filtros seleccionados</p>
                </td></tr>
              ) : data?.items.map((o) => (
                <tr key={o.id} className="border-t border-border hover:bg-muted/20 cursor-pointer" onClick={() => setDetailOrder(o)}>
                  <td className="px-4 py-3 font-mono text-xs font-bold text-brand-700">{o.order_number}</td>
                  <td className="px-4 py-3 text-xs hidden sm:table-cell">{o.channel}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">{formatDate(o.occurred_at)}</td>
                  <td className="px-4 py-3 text-right font-semibold">{formatCurrency(Number(o.grand_total))}</td>
                  <td className="px-4 py-3 text-right text-muted-foreground hidden md:table-cell">
                    {Number(o.balance_due) > 0 ? <span className="text-rose-500 font-medium">{formatCurrency(Number(o.balance_due))}</span> : <span className="text-emerald-500">✓</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge variant={STATUS_BADGE[o.payment_status] ?? 'neutral'}>{o.payment_status}</Badge>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge variant={o.status === 'cancelled' ? 'danger' : 'success'}>
                      {o.status === 'cancelled' ? 'Anulada' : o.status === 'confirmed' ? 'Activa' : o.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button className="p-1.5 rounded text-muted-foreground hover:text-brand-600 hover:bg-brand-50 transition" onClick={(e) => { e.stopPropagation(); setDetailOrder(o); }}>
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

      {detailOrder && (
        <OrderDetailModal
          order={detailOrder}
          onClose={() => setDetailOrder(null)}
          onCancelDone={() => setDetailOrder(null)}
          onPaymentDone={() => setDetailOrder(null)}
        />
      )}
    </div>
  );
}

