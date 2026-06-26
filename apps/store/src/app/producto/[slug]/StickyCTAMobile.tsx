'use client';

import { useEffect, useRef, useState } from 'react';
import { ShoppingBag } from 'lucide-react';
import { toast } from 'sonner';
import { useCart, type CartItem } from '@/lib/cart-store';

interface Props {
  product: Omit<CartItem, 'quantity'>;
  inStock: boolean;
}

export function StickyCTAMobile({ product, inStock }: Props) {
  const [show, setShow] = useState(false);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const add = useCart((s) => s.add);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => setShow(!entry.isIntersecting),
      { threshold: 0 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <>
      <div ref={sentinelRef} />
      {show && (
        <div className="fixed bottom-0 left-0 right-0 md:hidden z-50 bg-white/95 backdrop-blur-sm border-t border-border px-4 py-3 flex gap-3 shadow-[0_-4px_20px_rgba(0,0,0,0.08)]">
          {inStock ? (
            <button
              onClick={() => {
                add(product, 1);
                toast.success(`${product.name} agregado al carrito`);
              }}
              className="flex-1 btn-primary py-3.5 text-base flex items-center justify-center gap-2"
            >
              <ShoppingBag className="h-5 w-5" />
              Agregar al carrito
            </button>
          ) : (
            <div className="flex-1 py-3.5 text-center rounded-2xl bg-gray-100 text-gray-500 font-semibold text-sm">
              Producto agotado
            </div>
          )}
        </div>
      )}
    </>
  );
}
