'use client';

import { useState, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Search, Plus, Minus, Trash2, ShoppingCart, User, CreditCard,
  Banknote, Smartphone, CheckCircle2, Printer, RotateCcw, X, XCircle,
  FileText, MessageCircle, History, Eye, ChevronRight,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { cn, formatCurrency, formatDate } from '@/lib/utils';
import { products, customers, pos, sales, API_BASE, type Product, type Customer, type Order } from '@/lib/api';
import { useAuth } from '@/lib/auth-store';
import { toast } from 'sonner';

// ─── Types ────────────────────────────────────────────────────────
interface CartItem {
  product: Product;
  quantity: number;
  unit_price: number;
  discount: number;
}

interface PaymentEntry {
  method: string;
  amount: string;
}

const PAYMENT_METHODS = [
  { key: 'Efectivo', icon: Banknote, label: 'Efectivo' },
  { key: 'Tarjeta', icon: CreditCard, label: 'Tarjeta' },
  { key: 'Nequi', icon: Smartphone, label: 'Nequi' },
  { key: 'Daviplata', icon: Smartphone, label: 'Daviplata' },
  { key: 'Transferencia', icon: CreditCard, label: 'Transferencia' },
];

// ─── WhatsApp message builder ─────────────────────────────────────
function buildWhatsAppMsg(order: Order, customerName?: string): string {
  const name = customerName || 'estimado cliente';
  const items = order.items.map((i) =>
    `  • ${i.name_snapshot} x${i.quantity} → ${formatCurrency(Number(i.line_total))}`
  ).join('\n');
  const change = Number(order.paid_amount) - Number(order.grand_total);
  const changeStr = change > 0 ? `\n💵 *Cambio:* ${formatCurrency(change)}` : '';
  return encodeURIComponent(
    `🐾 *¡Gracias por visitarnos, ${name}!* 🐾\n\n` +
    `Tu compra en *Bigotes y Paticas* fue registrada exitosamente 🎉\n\n` +
    `📋 *Orden:* ${order.order_number}\n` +
    `📅 *Fecha:* ${new Date(order.occurred_at).toLocaleDateString('es-CO', { dateStyle: 'medium' })}\n\n` +
    `🛍️ *Productos:*\n${items}\n\n` +
    `💰 *Total:* *${formatCurrency(Number(order.grand_total))}*\n` +
    `💳 *Pago:* ${order.payment_method || order.payments?.[0]?.method || '—'}${changeStr}\n\n` +
    `¡Tus mascotas son lo más especial! 🐶🐱\n` +
    `Gracias por confiar en nosotros. ¡Hasta pronto! 🐾✨`
  );
}

// ─── Product Search ───────────────────────────────────────────────
function ProductSearch({ onAdd }: { onAdd: (p: Product) => void }) {
  const [q, setQ] = useState('');

  const { data, isFetching } = useQuery({
    queryKey: ['pos-products', q],
    queryFn: () => products.list({ q: q || undefined, page_size: 12 }),
    enabled: true,
    staleTime: 30_000,
  });

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Buscar producto por nombre o SKU…"
          className="pl-9"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-3 gap-2 max-h-[340px] overflow-y-auto pr-1">
        {isFetching && !data && (
          [...Array(6)].map((_, i) => (
            <div key={i} className="h-20 bg-muted/30 animate-pulse rounded-lg" />
          ))
        )}
        {data?.items.map((p) => (
          <button
            key={p.id}
            onClick={() => onAdd(p)}
            className="group flex flex-col gap-1 p-3 rounded-lg border border-border hover:border-brand/40 hover:bg-brand/5 transition-all text-left"
          >
            {p.primary_image_url ? (
              <img src={p.primary_image_url} alt="" className="h-10 w-10 rounded object-cover mb-1" />
            ) : (
              <div className="h-10 w-10 rounded bg-muted flex items-center justify-center text-xl mb-1">📦</div>
            )}
            <div className="font-medium text-sm leading-tight line-clamp-2">{p.name}</div>
            <div className="text-xs text-muted-foreground font-mono">{p.sku}</div>
            <div className="text-sm font-bold text-brand-700">{formatCurrency(Number(p.price))}</div>
          </button>
        ))}
        {data?.items.length === 0 && (
          <div className="col-span-full py-8 text-center text-muted-foreground text-sm">
            Sin resultados para "{q}"
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Customer Selector ────────────────────────────────────────────
function CustomerSelector({
  value,
  onChange,
}: {
  value: Customer | null;
  onChange: (c: Customer | null) => void;
}) {
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const { data } = useQuery({
    queryKey: ['pos-customers', q],
    queryFn: () => customers.list({ q: q || undefined, page_size: 8 }),
    enabled: open,
  });

  if (value) {
    return (
      <div className="flex items-center justify-between p-3 rounded-lg border border-brand/30 bg-brand/5">
        <div className="flex items-center gap-2">
          <User className="h-4 w-4 text-brand-600" />
          <div>
            <div className="font-medium text-sm">{value.full_name}</div>
            {value.phone && <div className="text-xs text-muted-foreground">{value.phone}</div>}
          </div>
        </div>
        <button onClick={() => onChange(null)} className="text-muted-foreground hover:text-foreground">
          <X className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="relative">
        <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Cliente (opcional) — nombre o teléfono"
          className="pl-9"
          value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 200)}
        />
      </div>
      {open && (data?.items.length ?? 0) > 0 && (
        <div className="rounded-lg border border-border shadow-elegant bg-background z-10">
          {data!.items.map((c) => (
            <button
              key={c.id}
              onMouseDown={() => { onChange(c); setOpen(false); setQ(''); }}
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-accent/50 text-sm text-left"
            >
              <div className="w-7 h-7 rounded-full gradient-brand flex items-center justify-center text-white text-xs font-bold shrink-0">
                {(c.full_name ?? '?').charAt(0)}
              </div>
              <div>
                <div className="font-medium">{c.full_name}</div>
                {c.phone && <div className="text-xs text-muted-foreground">{c.phone}</div>}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Order Detail Modal ───────────────────────────────────────────
function OrderDetailModal({ order, onClose, onCancel }: { order: Order; onClose: () => void; onCancel: (id: string) => void }) {
  const token = useAuth((s) => s.token);

  function openInvoice() {
    fetch(`${API_BASE}/v1/sales/orders/${order.id}/invoice`, {
      headers: { Authorization: `Bearer ${token ?? ''}` },
    })
      .then((r) => { if (!r.ok) throw new Error('Error'); return r.blob(); })
      .then((blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `comprobante-${order.order_number}.html`;
        a.click();
      })
      .catch(() => toast.error('Error generando comprobante'));
  }

  const waMsg = buildWhatsAppMsg(order);

  return (
    <Dialog open onClose={onClose} title={`Orden ${order.order_number}`} size="md">
      <DialogBody className="space-y-4">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><span className="text-muted-foreground">Canal:</span> <span className="font-medium">{order.channel}</span></div>
          <div><span className="text-muted-foreground">Fecha:</span> <span className="font-medium">{formatDate(order.occurred_at)}</span></div>
          <div><span className="text-muted-foreground">Estado:</span> <Badge variant={order.status === 'cancelled' ? 'danger' : 'success'}>{order.status}</Badge></div>
          <div><span className="text-muted-foreground">Pago:</span> <Badge variant={order.payment_status === 'Pagado' ? 'success' : order.payment_status === 'Abono parcial' ? 'warning' : 'danger'}>{order.payment_status}</Badge></div>
        </div>

        <table className="w-full text-sm border border-border rounded-xl overflow-hidden">
          <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="text-left px-3 py-2">Producto</th>
              <th className="text-right px-3 py-2">Cant.</th>
              <th className="text-right px-3 py-2">Precio</th>
              <th className="text-right px-3 py-2">Total</th>
            </tr>
          </thead>
          <tbody>
            {order.items.map((it) => (
              <tr key={it.id} className="border-t border-border">
                <td className="px-3 py-2"><div className="font-medium">{it.name_snapshot}</div><div className="text-xs text-muted-foreground font-mono">{it.sku_snapshot}</div></td>
                <td className="px-3 py-2 text-right">{it.quantity}</td>
                <td className="px-3 py-2 text-right">{formatCurrency(Number(it.unit_price))}</td>
                <td className="px-3 py-2 text-right font-semibold">{formatCurrency(Number(it.line_total))}</td>
              </tr>
            ))}
          </tbody>
          <tfoot className="bg-muted/30 font-bold border-t border-border text-sm">
            <tr><td colSpan={3} className="px-3 py-2 text-right">Total</td><td className="px-3 py-2 text-right text-emerald-700">{formatCurrency(Number(order.grand_total))}</td></tr>
          </tfoot>
        </table>

        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" size="sm" onClick={openInvoice}><FileText className="w-4 h-4 mr-1" /> Comprobante</Button>
          <a href={`https://wa.me/?text=${waMsg}`} target="_blank" rel="noopener noreferrer">
            <Button variant="outline" size="sm" className="text-emerald-700 border-emerald-300 hover:bg-emerald-50">
              <MessageCircle className="w-4 h-4 mr-1" /> WhatsApp
            </Button>
          </a>
          {order.status !== 'cancelled' && (
            <Button variant="outline" size="sm" className="text-rose-600 border-rose-200 hover:bg-rose-50" onClick={() => { onCancel(order.id); onClose(); }}>
              <XCircle className="w-4 h-4 mr-1" /> Anular
            </Button>
          )}
        </div>
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cerrar</Button>
      </DialogFooter>
    </Dialog>
  );
}

// ─── Sales History Panel ──────────────────────────────────────────
function SalesHistoryPanel() {
  const token = useAuth((s) => s.token);
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [detailOrder, setDetailOrder] = useState<Order | null>(null);
  const [cancelTarget, setCancelTarget] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['pos-history', page, search],
    queryFn: () => sales.list({ q: search || undefined, page, page_size: 20 }),
    staleTime: 15_000,
  });

  const cancelMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => sales.cancel(id, reason),
    onSuccess: () => {
      toast.success('Venta anulada — stock revertido');
      qc.invalidateQueries({ queryKey: ['pos-history'] });
      qc.invalidateQueries({ queryKey: ['inventory-stock'] });
      setCancelTarget(null);
      setCancelReason('');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Buscar por # orden…" className="pl-9" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
      </div>

      <div className="rounded-xl border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="text-left px-3 py-2">Orden</th>
              <th className="text-left px-3 py-2 hidden sm:table-cell">Fecha</th>
              <th className="text-right px-3 py-2">Total</th>
              <th className="text-center px-3 py-2">Estado</th>
              <th className="text-center px-3 py-2">Acc.</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? Array.from({ length: 5 }).map((_, i) => (
              <tr key={i} className="border-t border-border"><td colSpan={5} className="px-3 py-2"><div className="h-4 bg-muted/40 rounded animate-pulse" /></td></tr>
            )) : data?.items.map((o) => (
              <tr key={o.id} className="border-t border-border hover:bg-muted/20 cursor-pointer" onClick={() => setDetailOrder(o)}>
                <td className="px-3 py-2 font-mono text-xs font-bold">{o.order_number}</td>
                <td className="px-3 py-2 text-xs text-muted-foreground hidden sm:table-cell">{formatDate(o.occurred_at)}</td>
                <td className="px-3 py-2 text-right font-semibold text-emerald-700">{formatCurrency(Number(o.grand_total))}</td>
                <td className="px-3 py-2 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${o.status === 'cancelled' ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'}`}>{o.status === 'cancelled' ? 'Anulada' : 'OK'}</span>
                </td>
                <td className="px-3 py-2 text-center">
                  <button className="p-1 rounded hover:bg-brand-50 text-muted-foreground hover:text-brand-600" onClick={(e) => { e.stopPropagation(); setDetailOrder(o); }}>
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.total > 20 && (
          <div className="px-3 py-2 flex items-center justify-between text-xs text-muted-foreground border-t border-border">
            <span>{data.total} ventas</span>
            <div className="flex gap-1">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="px-2 py-1 rounded border border-border disabled:opacity-40">‹</button>
              <span className="px-2 py-1">{page}</span>
              <button onClick={() => setPage((p) => p + 1)} disabled={page * 20 >= data.total} className="px-2 py-1 rounded border border-border disabled:opacity-40">›</button>
            </div>
          </div>
        )}
      </div>

      {detailOrder && (
        <OrderDetailModal
          order={detailOrder}
          onClose={() => setDetailOrder(null)}
          onCancel={(id) => setCancelTarget(id)}
        />
      )}

      <Dialog open={!!cancelTarget} onClose={() => { setCancelTarget(null); setCancelReason(''); }} title="Anular venta" size="sm">
        <DialogBody className="space-y-3">
          <p className="text-sm text-muted-foreground">La orden será anulada y el stock será revertido automáticamente. Esta acción no se puede deshacer.</p>
          <div>
            <label className="text-xs font-medium mb-1 block text-muted-foreground uppercase">Motivo (opcional)</label>
            <Input value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} placeholder="Ej: error en la venta, devolución…" />
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => { setCancelTarget(null); setCancelReason(''); }}>Volver</Button>
          <Button variant="destructive" disabled={cancelMut.isPending} onClick={() => cancelTarget && cancelMut.mutate({ id: cancelTarget, reason: cancelReason })}>
            {cancelMut.isPending ? 'Anulando…' : 'Confirmar anulación'}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}

// ─── Success Screen ───────────────────────────────────────────────
function SuccessScreen({ order, customer, onNew }: { order: Order; customer: Customer | null; onNew: () => void }) {
  const token = useAuth((s) => s.token);
  const qc = useQueryClient();
  const [cancelled, setCancelled] = useState(false);

  const cancelMut = useMutation({
    mutationFn: () => sales.cancel(order.id, 'Cancelado desde POS'),
    onSuccess: () => {
      setCancelled(true);
      toast.success('Venta anulada y stock revertido');
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['pos-history'] });
      qc.invalidateQueries({ queryKey: ['inventory-stock'] });
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

  const customerName = customer?.full_name;
  const customerPhone = customer?.phone?.replace(/\D/g, '');
  const waText = buildWhatsAppMsg(order, customerName ?? undefined);
  const waUrl = customerPhone
    ? `https://wa.me/57${customerPhone}?text=${waText}`
    : `https://wa.me/?text=${waText}`;

  const change = Number(order.paid_amount) - Number(order.grand_total);

  return (
    <div className="flex flex-col items-center justify-center min-h-[500px] gap-5 text-center py-8 px-4">
      {/* Icon */}
      <div className={`w-24 h-24 rounded-full flex items-center justify-center shadow-glow text-5xl ${cancelled ? 'bg-rose-100' : 'bg-emerald-100'}`}>
        {cancelled ? '❌' : '🎉'}
      </div>

      {/* Title */}
      <div>
        <h2 className="text-3xl font-display font-bold">{cancelled ? 'Venta anulada' : '¡Venta registrada!'}</h2>
        <p className="text-muted-foreground mt-1">
          Orden <span className="font-mono font-bold text-brand-700">#{order.order_number}</span>
          {customerName && <span className="ml-2">· {customerName}</span>}
        </p>
      </div>

      {/* Receipt card */}
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card shadow-sm p-5 text-left space-y-2">
        <div className="text-xs uppercase text-muted-foreground font-semibold mb-3 border-b border-border pb-2">Resumen de compra</div>
        {order.items.map((it) => (
          <div key={it.id} className="flex justify-between text-sm">
            <span className="text-muted-foreground truncate mr-2">{it.name_snapshot} ×{it.quantity}</span>
            <span className="font-medium shrink-0">{formatCurrency(Number(it.line_total))}</span>
          </div>
        ))}
        <div className="border-t border-border pt-2 mt-2 space-y-1">
          <div className="flex justify-between font-bold text-base">
            <span>Total</span>
            <span className="text-brand-700">{formatCurrency(Number(order.grand_total))}</span>
          </div>
          <div className="flex justify-between text-sm text-emerald-600">
            <span>Recibido</span>
            <span className="font-semibold">{formatCurrency(Number(order.paid_amount))}</span>
          </div>
          {change > 0 && (
            <div className="flex justify-between text-sm font-semibold text-amber-600">
              <span>Cambio</span>
              <span>{formatCurrency(change)}</span>
            </div>
          )}
          {Number(order.balance_due) > 0 && (
            <div className="flex justify-between text-sm font-semibold text-rose-600">
              <span>Saldo pendiente</span>
              <span>{formatCurrency(Number(order.balance_due))}</span>
            </div>
          )}
          <div className="flex justify-between text-xs text-muted-foreground pt-1">
            <span>Método</span>
            <span>{order.payment_method || order.payments?.[0]?.method || '—'}</span>
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2 flex-wrap justify-center w-full max-w-sm">
        {!cancelled && (
          <a href={waUrl} target="_blank" rel="noopener noreferrer" className="flex-1">
            <Button className="w-full bg-[#25D366] hover:bg-[#1fba58] text-white font-semibold shadow-sm">
              <MessageCircle className="h-4 w-4 mr-2" />
              WhatsApp
            </Button>
          </a>
        )}
        <Button variant="outline" onClick={downloadInvoice} className="flex-1">
          <FileText className="h-4 w-4 mr-2" /> Comprobante
        </Button>
        <Button variant="outline" onClick={() => window.print()} className="flex-1">
          <Printer className="h-4 w-4 mr-2" /> Imprimir
        </Button>
      </div>

      <div className="flex gap-2 flex-wrap justify-center">
        {!cancelled && (
          <Button
            variant="outline"
            onClick={() => cancelMut.mutate()}
            disabled={cancelMut.isPending}
            className="text-rose-600 border-rose-200 hover:bg-rose-50"
          >
            <XCircle className="h-4 w-4 mr-2" />
            {cancelMut.isPending ? 'Anulando…' : 'Anular venta'}
          </Button>
        )}
        <Button onClick={onNew} className="font-semibold">
          <RotateCcw className="h-4 w-4 mr-2" /> Nueva venta
        </Button>
      </div>
    </div>
  );
}

// ─── POS Main ─────────────────────────────────────────────────────
export default function POSPage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<'venta' | 'historial'>('venta');
  const [cart, setCart] = useState<CartItem[]>([]);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [payments, setPayments] = useState<PaymentEntry[]>([{ method: 'Efectivo', amount: '' }]);
  const [notes, setNotes] = useState('');
  const [completedOrder, setCompletedOrder] = useState<Order | null>(null);

  // ── Cart helpers ──
  const addProduct = useCallback((p: Product) => {
    setCart((prev) => {
      const idx = prev.findIndex((i) => i.product.id === p.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = { ...next[idx], quantity: next[idx].quantity + 1 };
        return next;
      }
      return [...prev, { product: p, quantity: 1, unit_price: Number(p.price), discount: 0 }];
    });
  }, []);

  const updateQty = (id: string, delta: number) => {
    setCart((prev) =>
      prev
        .map((i) => i.product.id === id ? { ...i, quantity: Math.max(1, i.quantity + delta) } : i)
        .filter((i) => i.quantity > 0),
    );
  };

  const removeItem = (id: string) => setCart((prev) => prev.filter((i) => i.product.id !== id));

  const updatePrice = (id: string, val: string) => {
    const n = parseFloat(val.replace(/\D/g, '')) || 0;
    setCart((prev) => prev.map((i) => i.product.id === id ? { ...i, unit_price: n } : i));
  };

  const updateDiscount = (id: string, val: string) => {
    const n = parseFloat(val.replace(/\D/g, '')) || 0;
    setCart((prev) => prev.map((i) => i.product.id === id ? { ...i, discount: n } : i));
  };

  // ── Totals ──
  const subtotal = cart.reduce((s, i) => s + i.unit_price * i.quantity, 0);
  const discounts = cart.reduce((s, i) => s + i.discount, 0);
  const grand = subtotal - discounts;
  const totalPaid = payments.reduce((s, p) => s + (parseFloat(p.amount) || 0), 0);
  const change = totalPaid - grand;

  // ── Payment helpers ──
  const updatePayment = (idx: number, field: 'method' | 'amount', val: string) => {
    setPayments((prev) => prev.map((p, i) => i === idx ? { ...p, [field]: val } : p));
  };
  const addPayment = () => setPayments((prev) => [...prev, { method: 'Efectivo', amount: '' }]);
  const removePayment = (idx: number) => setPayments((prev) => prev.filter((_, i) => i !== idx));
  const fillAmount = () => {
    const remaining = grand - payments.slice(0, -1).reduce((s, p) => s + (parseFloat(p.amount) || 0), 0);
    setPayments((prev) => prev.map((p, i) => i === prev.length - 1 ? { ...p, amount: String(Math.max(0, remaining)) } : p));
  };

  // ── Submit ──
  const mutation = useMutation({
    mutationFn: () =>
      pos.createOrder({
        customer_id: customer?.id,
        channel: 'POS',
        items: cart.map((i) => ({
          product_id: i.product.id,
          quantity: i.quantity,
          unit_price: i.unit_price,
          discount: i.discount,
        })),
        payments: payments
          .filter((p) => parseFloat(p.amount) > 0)
          .map((p) => ({ method: p.method, amount: parseFloat(p.amount) })),
        notes: notes || undefined,
      }),
    onSuccess: (order) => {
      setCompletedOrder(order);
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['pos-history'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      qc.invalidateQueries({ queryKey: ['stock-alerts'] });
      qc.invalidateQueries({ queryKey: ['inventory-stock'] });
    },
  });

  const resetAll = () => {
    setCart([]);
    setCustomer(null);
    setPayments([{ method: 'Efectivo', amount: '' }]);
    setNotes('');
    setCompletedOrder(null);
    mutation.reset();
  };

  if (completedOrder) {
    return (
      <div className="max-w-2xl mx-auto">
        <SuccessScreen order={completedOrder} customer={customer} onNew={resetAll} />
      </div>
    );
  }

  const canSubmit = cart.length > 0 && !mutation.isPending;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight">Punto de Venta</h1>
          <p className="text-muted-foreground text-sm mt-1">Registra ventas · stock se descuenta automáticamente</p>
        </div>
        <div className="flex gap-1 border border-border rounded-lg p-0.5">
          {[{ id: 'venta', label: 'Nueva venta', icon: ShoppingCart }, { id: 'historial', label: 'Historial', icon: History }].map((t) => (
            <button key={t.id} onClick={() => setActiveTab(t.id as 'venta' | 'historial')} className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium transition-colors ${activeTab === t.id ? 'bg-brand-600 text-white' : 'text-muted-foreground hover:text-foreground'}`}>
              <t.icon className="w-4 h-4" /> {t.label}
              {t.id === 'venta' && cart.length > 0 && <span className="ml-1 bg-white/20 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs">{cart.length}</span>}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'historial' ? (
        <SalesHistoryPanel />
      ) : (
        <div className="grid lg:grid-cols-[1fr_400px] gap-4 items-start">
          {/* ── LEFT: Products + Cart ── */}
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Catálogo</CardTitle>
              </CardHeader>
              <CardContent>
                <ProductSearch onAdd={addProduct} />
              </CardContent>
            </Card>

            {/* Cart */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <ShoppingCart className="h-4 w-4" />
                    Carrito ({cart.length})
                  </CardTitle>
                  {cart.length > 0 && (
                    <button onClick={() => setCart([])} className="text-xs text-muted-foreground hover:text-destructive">
                      Vaciar todo
                    </button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {cart.length === 0 ? (
                  <div className="py-10 text-center text-muted-foreground text-sm">
                    <ShoppingCart className="h-8 w-8 mx-auto mb-2 opacity-20" />
                    Agrega productos del catálogo
                  </div>
                ) : (
                  <div className="divide-y divide-border/40">
                    {cart.map((item) => (
                      <div key={item.product.id} className="flex gap-3 p-3 items-start">
                        {/* Name + SKU */}
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm leading-tight">{item.product.name}</div>
                          <div className="text-xs text-muted-foreground font-mono">{item.product.sku}</div>
                          <div className="flex gap-2 mt-2">
                            {/* Price input */}
                            <div className="flex flex-col gap-0.5">
                              <label className="text-[10px] text-muted-foreground">Precio</label>
                              <input
                                type="number"
                                value={item.unit_price}
                                onChange={(e) => updatePrice(item.product.id, e.target.value)}
                                className="w-28 h-7 px-2 text-sm rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-brand/50"
                              />
                            </div>
                            {/* Discount */}
                            <div className="flex flex-col gap-0.5">
                              <label className="text-[10px] text-muted-foreground">Descuento</label>
                              <input
                                type="number"
                                value={item.discount}
                                onChange={(e) => updateDiscount(item.product.id, e.target.value)}
                                className="w-24 h-7 px-2 text-sm rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-brand/50"
                              />
                            </div>
                          </div>
                        </div>
                        {/* Qty + Total + Remove */}
                        <div className="flex flex-col items-end gap-2 shrink-0">
                          <button onClick={() => removeItem(item.product.id)} className="text-muted-foreground hover:text-destructive">
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                          <div className="flex items-center gap-1.5">
                            <button
                              onClick={() => updateQty(item.product.id, -1)}
                              className="w-6 h-6 rounded border border-border hover:bg-accent/50 flex items-center justify-center"
                            >
                              <Minus className="h-3 w-3" />
                            </button>
                            <span className="w-8 text-center font-semibold text-sm tabular-nums">{item.quantity}</span>
                            <button
                              onClick={() => updateQty(item.product.id, 1)}
                              className="w-6 h-6 rounded border border-border hover:bg-accent/50 flex items-center justify-center"
                            >
                              <Plus className="h-3 w-3" />
                            </button>
                          </div>
                          <div className="text-sm font-bold text-brand-700 tabular-nums">
                            {formatCurrency(item.unit_price * item.quantity - item.discount)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* ── RIGHT: Payment panel ── */}
          <div className="space-y-4">
            {/* Customer */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Cliente</CardTitle>
              </CardHeader>
              <CardContent>
                <CustomerSelector value={customer} onChange={setCustomer} />
              </CardContent>
            </Card>

            {/* Totals */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Resumen</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>Subtotal</span>
                  <span>{formatCurrency(subtotal)}</span>
                </div>
                {discounts > 0 && (
                  <div className="flex justify-between text-sm text-emerald-600">
                    <span>Descuentos</span>
                    <span>-{formatCurrency(discounts)}</span>
                  </div>
                )}
                <div className="flex justify-between font-bold text-lg pt-1 border-t border-border/60">
                  <span>Total</span>
                  <span className="text-brand-700">{formatCurrency(grand)}</span>
                </div>
              </CardContent>
            </Card>

            {/* Payments */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Pagos</CardTitle>
                  {payments.length < 3 && (
                    <button onClick={addPayment} className="text-xs text-brand-600 hover:text-brand-700 font-medium">
                      + Agregar método
                    </button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                {payments.map((pay, idx) => (
                  <div key={idx} className="flex gap-2 items-center">
                    <select
                      value={pay.method}
                      onChange={(e) => updatePayment(idx, 'method', e.target.value)}
                      className="flex-1 h-9 px-2 text-sm rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-brand/50"
                    >
                      {PAYMENT_METHODS.map((m) => (
                        <option key={m.key} value={m.key}>{m.label}</option>
                      ))}
                    </select>
                    <input
                      type="number"
                      placeholder="Monto"
                      value={pay.amount}
                      onChange={(e) => updatePayment(idx, 'amount', e.target.value)}
                      onFocus={() => !pay.amount && idx === payments.length - 1 && fillAmount()}
                      className="w-32 h-9 px-2 text-sm rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-brand/50 tabular-nums"
                    />
                    {payments.length > 1 && (
                      <button onClick={() => removePayment(idx)} className="text-muted-foreground hover:text-destructive shrink-0">
                        <X className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                ))}

                {/* Pagado / Cambio / Saldo */}
                {totalPaid > 0 && (
                  <div className="pt-2 space-y-1 border-t border-border/40 text-sm">
                    <div className="flex justify-between text-muted-foreground">
                      <span>Pagado</span>
                      <span>{formatCurrency(totalPaid)}</span>
                    </div>
                    {change >= 0 ? (
                      <div className="flex justify-between font-semibold text-emerald-600">
                        <span>Cambio</span>
                        <span>{formatCurrency(change)}</span>
                      </div>
                    ) : (
                      <div className="flex justify-between font-semibold text-rose-600">
                        <span>Saldo pendiente</span>
                        <span>{formatCurrency(Math.abs(change))}</span>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Notes */}
            <div>
              <textarea
                placeholder="Notas (opcional)"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background resize-none focus:outline-none focus:ring-1 focus:ring-brand/50"
              />
            </div>

            {/* Error */}
            {mutation.isError && (
              <div className="rounded-lg bg-rose-50 border border-rose-200 text-rose-700 px-3 py-2 text-sm">
                {mutation.error instanceof Error ? mutation.error.message : 'Error al registrar la venta'}
              </div>
            )}

            {/* Submit */}
            <Button
              className="w-full h-12 text-base font-semibold gradient-brand text-white hover:opacity-90 transition-opacity shadow-elegant"
              onClick={() => mutation.mutate()}
              disabled={!canSubmit}
            >
              {mutation.isPending ? (
                <div className="h-5 w-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <CheckCircle2 className="h-5 w-5 mr-2" />
                  Registrar venta — {formatCurrency(grand)}
                </>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
