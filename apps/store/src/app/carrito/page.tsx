'use client';

import Link from 'next/link';
import { Trash2, ShoppingBag, Star } from 'lucide-react';
import { useCart } from '@/lib/cart-store';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { formatCurrency } from '@/lib/utils';
import { storeApi } from '@/lib/api';

const GOOGLE_REVIEW_URL = 'https://g.page/r/CfL67OgLB-10EBM/review';

function trackGA4(event: string, params?: Record<string, unknown>) {
  if (typeof window !== 'undefined' && (window as unknown as { gtag?: (...args: unknown[]) => void }).gtag) {
    (window as unknown as { gtag: (...args: unknown[]) => void }).gtag('event', event, params);
  }
}

export default function CartPage() {
  const items = useCart((s) => s.items);
  const subtotal = useCart((s) => s.subtotal());
  const setQty = useCart((s) => s.setQty);
  const remove = useCart((s) => s.remove);
  const clear = useCart((s) => s.clear);

  const firstCategorySlug = items[0]?.slug?.split('-')[0] ?? undefined;

  const { data: suggestedData } = useQuery({
    queryKey: ['cross-sell', firstCategorySlug],
    queryFn: () =>
      storeApi.list({
        category_slug: firstCategorySlug,
        per_page: 8,
      }),
    enabled: true,
  });

  const suggested = (suggestedData?.items ?? [])
    .filter((p: { id: string }) => !items.find((i) => i.productId === p.id))
    .slice(0, 4);

  const shipping = subtotal >= 30000 ? 0 : 8000;
  const total = subtotal + shipping;

  const shareCart = () => {
    const names = items.map((i) => `${i.quantity}x ${i.name}`).join(', ');
    const msg = encodeURIComponent(
      `¡Mira lo que encontré en Bigotes y Paticas! 🐾\n${names}\n\n👉 https://bigotesypaticas.com`
    );
    window.open(`https://wa.me/?text=${msg}`, '_blank');
  };

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
    <div className="container-tight py-12">
      {/* Sección 1 — Carrito + Resumen */}
      <div className="grid lg:grid-cols-3 gap-8">
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
              <span>{shipping === 0 ? 'Gratis 🎉' : formatCurrency(shipping)}</span>
            </div>
            <div className="border-t border-border pt-4 flex justify-between font-bold">
              <span>Total</span>
              <span className="text-gradient text-xl">{formatCurrency(total)}</span>
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

      {/* Sección 2 — Cross-sell */}
      {suggested.length > 0 && (
        <div className="py-12 mt-4">
          <h2 className="text-xl font-display font-bold mb-6">También podría interesarte</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {suggested.map((p) => (
              <div key={p.id} className="rounded-2xl border border-border bg-card p-3 flex flex-col gap-2">
                <div className="aspect-square rounded-xl bg-secondary overflow-hidden flex items-center justify-center">
                  {p.primary_image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={p.primary_image_url} alt={p.name} className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-4xl">🐾</span>
                  )}
                </div>
                <p className="text-sm font-medium line-clamp-2">{p.name}</p>
                <p className="text-sm font-bold text-brand">{formatCurrency(parseFloat(p.price) || 0)}</p>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full mt-auto"
                  onClick={() => {
                    useCart.getState().add({ productId: p.id, slug: p.slug, name: p.name, price: parseFloat(p.price) || 0, image: p.primary_image_url ?? null });
                  }}
                >
                  + Agregar
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sección 3 — Banner App PWA */}
      <div className="py-12">
        <div className="rounded-3xl p-8 md:p-10" style={{ background: 'linear-gradient(135deg, #187f77 0%, #0d4a45 100%)' }}>
          <div className="max-w-xl">
            <h3 className="text-2xl md:text-3xl font-display font-bold text-white mb-2">
              📱 Descarga la App Bigotes
            </h3>
            <p className="text-white/80 mb-6">
              Carnet digital de tu mascota + recordatorios + 5% extra de Puntos en cada compra
            </p>
            <ul className="space-y-2 mb-8">
              {[
                'Pide en 1 clic con tu historial guardado',
                'Recordatorios de vacunas y desparasitación',
                'Comparte con un amigo, ambos ganan puntos',
              ].map((item) => (
                <li key={item} className="flex items-center gap-2 text-white/90 text-sm">
                  <span className="text-green-300 font-bold">✓</span> {item}
                </li>
              ))}
            </ul>
            <a href="https://mi.bigotesypaticas.com/registro" target="_blank" rel="noopener noreferrer">
              <Button
                size="lg"
                className="bg-white text-[#187f77] hover:bg-white/90 font-bold"
              >
                Crear cuenta gratis →
              </Button>
            </a>
          </div>
        </div>
      </div>

      {/* Sección 4 — Trust signals */}
      <div className="py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { icon: '🚚', title: 'Envío GRATIS desde $30.000', desc: 'Entrega en 24-72h en Pereira y Dosquebradas' },
            { icon: '🛡️', title: 'Pago seguro', desc: 'Datos protegidos · Transacciones encriptadas' },
            { icon: '↩️', title: 'Devoluciones gratis', desc: '30 días sin complicaciones' },
          ].map((item) => (
            <div key={item.title} className="flex items-start gap-4 p-5 rounded-2xl border border-border bg-card">
              <span className="text-3xl">{item.icon}</span>
              <div>
                <p className="font-semibold text-sm">{item.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Sección 5 — Compartir carrito */}
      <div className="py-12 text-center">
        <h3 className="text-lg font-display font-semibold mb-2">¿Conoces a alguien que necesite estos productos?</h3>
        <p className="text-muted-foreground text-sm mb-5">Comparte tu carrito por WhatsApp</p>
        <Button
          onClick={shareCart}
          className="bg-[#25D366] hover:bg-[#20b358] text-white font-bold gap-2"
          size="lg"
        >
          <span>💬</span> Compartir por WhatsApp
        </Button>
      </div>

      {/* Sección 6 — Métodos de pago */}
      <div className="py-12 border-t border-border">
        <h3 className="text-lg font-display font-semibold mb-4 text-center">Métodos de pago aceptados</h3>
        <div className="flex flex-wrap justify-center gap-3 mb-4">
          {['💵 Efectivo', '💳 Visa', '💳 Mastercard', '📱 Nequi', '📱 Daviplata', '🏦 PSE'].map((m) => (
            <span key={m} className="px-4 py-2 rounded-xl border border-border bg-card text-sm font-medium">{m}</span>
          ))}
        </div>
        <p className="text-center text-sm text-muted-foreground">
          💳 Pago contra entrega disponible en Pereira y Dosquebradas
        </p>
      </div>

      {/* Sección 7 — Google Review CTA */}
      <div className="py-12 border-t border-border text-center">
        <div className="flex justify-center gap-1 mb-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <Star key={i} className="w-7 h-7 fill-yellow-400 text-yellow-400" />
          ))}
        </div>
        <h3 className="text-lg font-display font-semibold mb-1">¿Has comprado antes? Califícanos en Google ⭐</h3>
        <p className="text-muted-foreground text-sm mb-5">Solo toma 30 segundos y nos ayuda muchísimo</p>
        <Button
          onClick={() => {
            window.open(GOOGLE_REVIEW_URL, '_blank');
            trackGA4('google_review_intent', { source: 'cart_page' });
          }}
          variant="outline"
          size="lg"
          className="border-yellow-400 text-yellow-600 hover:bg-yellow-50 font-semibold"
        >
          Dejar reseña en Google →
        </Button>
      </div>
    </div>
  );
}
