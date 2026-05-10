'use client';

import Link from 'next/link';
import { Trash2, ShoppingBag } from 'lucide-react';
import { useCart } from '@/lib/cart-store';
import { Button } from '@/components/ui/button';
import { formatCurrency } from '@/lib/utils';

export default function CartPage() {
  const items = useCart((s) => s.items);
  const subtotal = useCart((s) => s.subtotal());
  const setQty = useCart((s) => s.setQty);
  const remove = useCart((s) => s.remove);
  const clear = useCart((s) => s.clear);

  if (items.length === 0) {
    return (
      <div className="container-tight py-24 text-center">
        <ShoppingBag className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
        <h1 className="text-3xl font-display font-bold">Tu carrito está vacío</h1>
        <p className="text-muted-foreground mt-2 mb-6">Explora la tienda y encuentra algo especial.</p>
        <Link href="/">
          <Button size="lg">Ver productos</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="container-tight py-12 grid lg:grid-cols-3 gap-8">
      <div className="lg:col-span-2 space-y-3">
        <h1 className="text-3xl font-display font-bold mb-6">Carrito ({items.length})</h1>
        {items.map((i) => (
          <div
            key={i.productId}
            className="flex gap-4 items-center p-4 rounded-2xl border border-border bg-card"
          >
            <div className="w-20 h-20 rounded-xl bg-secondary overflow-hidden flex items-center justify-center text-3xl shrink-0">
              {i.image ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={i.image} alt={i.name} className="w-full h-full object-cover" />
              ) : (
                '🐾'
              )}
            </div>
            <div className="flex-1 min-w-0">
              <Link href={`/producto/${i.slug}`} className="font-medium hover:text-brand line-clamp-1">
                {i.name}
              </Link>
              <div className="text-sm text-muted-foreground">{formatCurrency(i.price)} c/u</div>
            </div>
            <input
              type="number"
              min={0}
              value={i.quantity}
              onChange={(e) => setQty(i.productId, parseInt(e.target.value) || 0)}
              className="w-16 h-9 px-2 rounded-lg border border-border bg-background text-center text-sm"
            />
            <div className="font-semibold w-24 text-right">{formatCurrency(i.price * i.quantity)}</div>
            <button
              onClick={() => remove(i.productId)}
              aria-label="Eliminar"
              className="text-muted-foreground hover:text-destructive p-2"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
        <button onClick={clear} className="text-xs text-muted-foreground hover:text-destructive mt-4">
          Vaciar carrito
        </button>
      </div>

      <aside className="lg:sticky lg:top-24 h-fit">
        <div className="rounded-2xl border border-border bg-card p-6 space-y-4">
          <h2 className="font-display font-semibold text-lg">Resumen</h2>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Subtotal</span>
            <span>{formatCurrency(subtotal)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Envío</span>
            <span>{subtotal >= 150000 ? 'Gratis' : formatCurrency(15000)}</span>
          </div>
          <div className="border-t border-border pt-4 flex justify-between font-bold">
            <span>Total</span>
            <span className="text-gradient text-xl">
              {formatCurrency(subtotal + (subtotal >= 150000 ? 0 : 15000))}
            </span>
          </div>
          <Link href="/checkout">
            <Button size="lg" className="w-full">
              Ir a pagar
            </Button>
          </Link>
          <p className="text-xs text-muted-foreground text-center">
            Pago seguro · Devoluciones 30 días
          </p>
        </div>
      </aside>
    </div>
  );
}
