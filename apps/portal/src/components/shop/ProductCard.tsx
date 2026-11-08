'use client';

import Image from 'next/image';
import { motion, AnimatePresence } from 'framer-motion';
import { Minus, Plus } from 'lucide-react';
import { usePortalCart } from '@/lib/cart-store';
import { formatCOP } from '@/lib/utils';
import type { ShopProduct } from './types';

/**
 * Tarjeta de producto del portal (8-nov-2026). Lo que hacen las apps grandes de
 * delivery: foto grande sobre blanco, precio claro y el "+" en la propia tarjeta;
 * al tocarlo se vuelve un contador sin abrir nada. Tocar la foto abre el detalle.
 */
export function ProductCard({ p, onOpen }: { p: ShopProduct; onOpen: (p: ShopProduct) => void }) {
  const qty = usePortalCart((s) => s.items.find((i) => i.product_id === p.id)?.quantity ?? 0);
  const addItem = usePortalCart((s) => s.addItem);
  const updateQuantity = usePortalCart((s) => s.updateQuantity);
  const agotado = p.in_stock === false;
  const descuento =
    p.compare_at_price && p.compare_at_price > p.price
      ? Math.round((1 - p.price / p.compare_at_price) * 100)
      : null;

  function sumar() {
    if (qty === 0) {
      addItem({ product_id: p.id, sku: p.sku ?? '', name: p.name, image_url: p.image_url, unit_price: p.price, quantity: 1 });
      if (typeof navigator !== 'undefined' && 'vibrate' in navigator) navigator.vibrate?.(8);
    } else {
      updateQuantity(p.id, qty + 1);
    }
  }

  return (
    <div className="group relative flex flex-col rounded-[1.35rem] bg-white shadow-[0_1px_2px_rgba(16,24,40,.04),0_4px_16px_rgba(16,24,40,.06)] overflow-hidden">
      <button
        type="button"
        onClick={() => onOpen(p)}
        className="relative aspect-square w-full bg-white active:scale-[0.98] transition-transform duration-150"
        aria-label={`Ver ${p.name}`}
      >
        {p.image_url ? (
          <Image
            src={p.image_url}
            alt={p.name}
            fill
            sizes="(max-width: 430px) 50vw, 200px"
            className={`object-contain p-3 ${agotado ? 'opacity-40 grayscale' : ''}`}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-4xl text-gray-300">🐾</div>
        )}
        {descuento && !agotado && (
          <span className="absolute left-2 top-2 rounded-full bg-coral px-2 py-0.5 text-[11px] font-bold text-white">
            -{descuento}%
          </span>
        )}
        {agotado && (
          <span className="absolute left-2 top-2 rounded-full bg-gray-900/80 px-2 py-0.5 text-[11px] font-semibold text-white">
            Agotado
          </span>
        )}
      </button>

      <div className="flex flex-1 flex-col gap-1 px-3 pb-3 pt-1">
        {p.brand && p.brand.toLowerCase() !== 'varios' && (
          <p className="text-[10.5px] font-semibold uppercase tracking-wide text-muted line-clamp-1">{p.brand}</p>
        )}
        <p className="text-[13px] font-medium leading-snug text-foreground line-clamp-2 min-h-[2.4em]">{p.name}</p>
        <div className="mt-auto flex items-end justify-between gap-2 pt-1">
          <div className="leading-tight">
            <p className="text-[15px] font-extrabold tracking-tight text-foreground">{formatCOP(p.price)}</p>
            {descuento && (
              <p className="text-[11px] text-muted line-through">{formatCOP(p.compare_at_price!)}</p>
            )}
          </div>

          {!agotado && (
            <AnimatePresence initial={false} mode="popLayout">
              {qty === 0 ? (
                <motion.button
                  key="add"
                  type="button"
                  onClick={sumar}
                  initial={{ scale: 0.6, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.6, opacity: 0 }}
                  transition={{ type: 'spring', stiffness: 520, damping: 30 }}
                  whileTap={{ scale: 0.9 }}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-700 text-white shadow-[0_4px_12px_rgba(24,127,119,.35)]"
                  aria-label={`Agregar ${p.name}`}
                >
                  <Plus className="h-5 w-5" strokeWidth={2.6} />
                </motion.button>
              ) : (
                <motion.div
                  key="stepper"
                  initial={{ width: 36, opacity: 0 }}
                  animate={{ width: 92, opacity: 1 }}
                  exit={{ width: 36, opacity: 0 }}
                  transition={{ type: 'spring', stiffness: 480, damping: 34 }}
                  className="flex h-9 shrink-0 items-center justify-between overflow-hidden rounded-full bg-primary-700 text-white"
                >
                  <button type="button" onClick={() => updateQuantity(p.id, qty - 1)} className="flex h-9 w-8 items-center justify-center" aria-label="Quitar uno">
                    <Minus className="h-4 w-4" strokeWidth={2.6} />
                  </button>
                  <motion.span key={qty} initial={{ y: 6, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="text-sm font-bold tabular-nums">
                    {qty}
                  </motion.span>
                  <button type="button" onClick={sumar} className="flex h-9 w-8 items-center justify-center" aria-label="Agregar uno">
                    <Plus className="h-4 w-4" strokeWidth={2.6} />
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          )}
        </div>
      </div>
    </div>
  );
}

export function ProductCardSkeleton() {
  return (
    <div className="flex flex-col overflow-hidden rounded-[1.35rem] bg-white shadow-[0_4px_16px_rgba(16,24,40,.05)]">
      <div className="aspect-square animate-pulse bg-gray-100" />
      <div className="space-y-2 p-3">
        <div className="h-2.5 w-1/3 animate-pulse rounded bg-gray-100" />
        <div className="h-3 w-full animate-pulse rounded bg-gray-100" />
        <div className="h-3 w-2/3 animate-pulse rounded bg-gray-100" />
        <div className="h-4 w-1/2 animate-pulse rounded bg-gray-100" />
      </div>
    </div>
  );
}
