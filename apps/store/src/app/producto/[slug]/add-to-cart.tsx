'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Minus, Plus, ShoppingBag } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { useCart, type CartItem } from '@/lib/cart-store';
import { useMetaPixelEvent } from '@/hooks/useMetaPixelEvent';

export function AddToCart({ product }: { product: Omit<CartItem, 'quantity'> }) {
  const [qty, setQty] = useState(1);
  const add = useCart((s) => s.add);
  const router = useRouter();
  const { track } = useMetaPixelEvent();

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <div className="flex items-center border border-border rounded-full">
          <button
            onClick={() => setQty((q) => Math.max(1, q - 1))}
            className="h-11 w-11 flex items-center justify-center hover:bg-accent rounded-l-full"
            aria-label="Disminuir"
          >
            <Minus className="h-4 w-4" />
          </button>
          <span className="w-12 text-center font-medium">{qty}</span>
          <button
            onClick={() => setQty((q) => q + 1)}
            className="h-11 w-11 flex items-center justify-center hover:bg-accent rounded-r-full"
            aria-label="Aumentar"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
        <Button
          size="lg"
          className="flex-1"
          onClick={() => {
            add(product, qty);
            track('AddToCart', {
              content_ids: [product.productId],
              content_name: product.name,
              value: Number(product.price) * qty,
              currency: 'COP',
              contents: [{ id: product.productId, quantity: qty, item_price: Number(product.price) }],
              content_type: 'product',
            });
            toast.success(`${product.name.slice(0, 35)}… agregado al carrito`, {
              icon: '🛒',
              duration: 4000,
              action: {
                label: 'Ver carrito',
                onClick: () => router.push('/carrito'),
              },
            });
          }}
        >
          <ShoppingBag className="h-4 w-4" /> Agregar al carrito
        </Button>
      </div>
    </div>
  );
}
