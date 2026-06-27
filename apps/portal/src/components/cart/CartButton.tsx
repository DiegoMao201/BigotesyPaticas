'use client';

import { useState } from 'react';
import { ShoppingCart } from 'lucide-react';
import { usePortalCart } from '@/lib/cart-store';
import { CartDrawer } from './CartDrawer';

export function CartButton() {
  const [open, setOpen] = useState(false);
  const itemCount = usePortalCart((s) => s.itemCount());

  if (itemCount === 0) return null;

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-24 right-4 z-30 w-14 h-14 rounded-full bg-teal-600 text-white shadow-lg flex items-center justify-center hover:bg-teal-700 transition"
        aria-label="Ver carrito"
      >
        <ShoppingCart className="h-6 w-6" />
        {itemCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-orange-500 text-white text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center">
            {itemCount > 9 ? '9+' : itemCount}
          </span>
        )}
      </button>
      <CartDrawer open={open} onClose={() => setOpen(false)} />
    </>
  );
}
