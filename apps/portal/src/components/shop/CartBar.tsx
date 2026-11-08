'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ShoppingBag, ChevronRight } from 'lucide-react';
import { usePortalCart } from '@/lib/cart-store';
import { formatCOP } from '@/lib/utils';
import { CartDrawer } from '@/components/cart/CartDrawer';
import { promesaEntrega } from './entrega';

/**
 * Barra del carrito pegada sobre la navegación (8-nov-2026). En la tienda reemplaza
 * al botón redondo flotante: dice cuántos productos y cuánto va, siempre a la vista,
 * como en las apps de domicilios. El total "salta" cada vez que cambia.
 */
export function CartBar() {
  const [open, setOpen] = useState(false);
  const count = usePortalCart((s) => s.itemCount());
  const subtotal = usePortalCart((s) => s.subtotal());

  return (
    <>
      <AnimatePresence>
        {count > 0 && (
          <motion.button
            type="button"
            onClick={() => setOpen(true)}
            initial={{ y: 80, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 80, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 420, damping: 34 }}
            whileTap={{ scale: 0.98 }}
            className="fixed inset-x-3 bottom-[78px] z-40 mx-auto flex max-w-[406px] items-center gap-3 rounded-2xl bg-gray-900 px-4 py-3 text-white shadow-[0_12px_32px_rgba(0,0,0,.28)] short:bottom-[58px]"
            aria-label="Ver carrito"
          >
            <span className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-white/10">
              <ShoppingBag className="h-5 w-5" />
              <motion.span
                key={count}
                initial={{ scale: 1.6 }}
                animate={{ scale: 1 }}
                className="absolute -right-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1 text-[11px] font-bold text-gray-900"
              >
                {count}
              </motion.span>
            </span>
            <span className="flex-1 text-left">
              <span className="block text-sm font-bold">Ver carrito</span>
              <span className="block text-[11px] text-white/60">Domicilio gratis · {promesaEntrega()}</span>
            </span>
            <motion.span key={subtotal} initial={{ y: -6, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="text-base font-extrabold tabular-nums">
              {formatCOP(subtotal)}
            </motion.span>
            <ChevronRight className="h-4 w-4 text-white/60" />
          </motion.button>
        )}
      </AnimatePresence>
      <CartDrawer open={open} onClose={() => setOpen(false)} />
    </>
  );
}
