'use client';

import { useState, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Search, Plus, Minus, Trash2, ShoppingCart, User, CreditCard,
  Banknote, Smartphone, CheckCircle2, Printer, RotateCcw, X,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cn, formatCurrency } from '@/lib/utils';
import { products, customers, pos, type Product, type Customer, type Order } from '@/lib/api';

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

// ─── Success Screen ───────────────────────────────────────────────
function SuccessScreen({ order, onNew }: { order: Order; onNew: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 text-center py-12">
      <div className="w-20 h-20 rounded-full gradient-brand flex items-center justify-center shadow-glow">
        <CheckCircle2 className="h-10 w-10 text-white" />
      </div>
      <div>
        <h2 className="text-2xl font-display font-bold">¡Venta registrada!</h2>
        <p className="text-muted-foreground mt-1">Orden <span className="font-mono font-bold text-brand-700">#{order.order_number}</span></p>
      </div>
      <div className="w-full max-w-xs space-y-2 text-left rounded-xl border border-border p-4 bg-card">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Total</span>
          <span className="font-bold">{formatCurrency(Number(order.grand_total))}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Pagado</span>
          <span className="font-semibold text-emerald-600">{formatCurrency(Number(order.paid_amount))}</span>
        </div>
        {Number(order.balance_due) > 0 && (
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Saldo</span>
            <span className="font-semibold text-rose-600">{formatCurrency(Number(order.balance_due))}</span>
          </div>
        )}
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Estado</span>
          <span className="font-medium">{order.payment_status}</span>
        </div>
      </div>
      <div className="flex gap-3">
        <Button variant="outline" onClick={() => window.print()}>
          <Printer className="h-4 w-4 mr-2" /> Imprimir
        </Button>
        <Button onClick={onNew}>
          <RotateCcw className="h-4 w-4 mr-2" /> Nueva venta
        </Button>
      </div>
    </div>
  );
}

// ─── POS Main ─────────────────────────────────────────────────────
export default function POSPage() {
  const qc = useQueryClient();
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
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      qc.invalidateQueries({ queryKey: ['stock-alerts'] });
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
      <div className="h-full">
        <SuccessScreen order={completedOrder} onNew={resetAll} />
      </div>
    );
  }

  const canSubmit = cart.length > 0 && !mutation.isPending;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-3xl font-display font-bold tracking-tight">Punto de Venta</h1>
        <p className="text-muted-foreground text-sm mt-1">Registra ventas en mostrador — stock se descuenta automáticamente</p>
      </div>

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
    </div>
  );
}
