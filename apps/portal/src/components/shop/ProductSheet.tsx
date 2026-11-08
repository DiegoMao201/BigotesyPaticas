'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { useQuery } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { Check, Minus, Plus, Star, X } from 'lucide-react';
import { toast } from 'sonner';
import { usePortalCart } from '@/lib/cart-store';
import { formatCOP, getSpeciesEmoji } from '@/lib/utils';
import type { ShopProduct } from './types';
import { promesaEntrega } from './entrega';

interface Pet { id: string; name: string; species: string }

/**
 * Detalle del producto como hoja que sube desde abajo (8-nov-2026). Antes el
 * detalle reemplazaba toda la pantalla y al volver se perdía el sitio en la
 * lista; una hoja deja ver de dónde vienes y se cierra deslizando hacia abajo.
 */
export function ProductSheet({
  product, pets, onClose,
}: { product: ShopProduct | null; pets: Pet[]; onClose: () => void }) {
  const addItem = usePortalCart((s) => s.addItem);
  const [qty, setQty] = useState(1);
  const [petId, setPetId] = useState('');
  const [notes, setNotes] = useState('');

  useEffect(() => { setQty(1); setPetId(pets.length === 1 ? pets[0].id : ''); setNotes(''); }, [product?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const { data: detalle } = useQuery({
    queryKey: ['producto-detalle', product?.slug],
    queryFn: () => fetch(`/api/v1/products/by-slug/${product!.slug}`).then((r) => (r.ok ? r.json() : null)),
    enabled: !!product?.slug,
    staleTime: 10 * 60 * 1000,
  });
  const ec = (detalle?.enriched_content ?? {}) as { descripcion_corta?: string; beneficios?: string[] };
  const descripcion = ec.descripcion_corta || detalle?.short_description || product?.short_description;
  const beneficios = (ec.beneficios ?? []).map((b) => String(b).replace(/^✓\s*/, '')).slice(0, 4);

  function agregar() {
    if (!product) return;
    const pet = pets.find((x) => x.id === petId);
    addItem({
      product_id: product.id,
      sku: product.sku ?? '',
      name: product.name,
      image_url: product.image_url,
      unit_price: product.price,
      quantity: qty,
      notes: [notes, pet ? `Para: ${pet.name}` : ''].filter(Boolean).join(' | ') || undefined,
    });
    toast.success('Agregado al carrito', { description: product.name, icon: <Check className="h-4 w-4" /> });
    onClose();
  }

  return (
    <AnimatePresence>
      {product && (
        <>
          <motion.div
            className="fixed inset-0 z-[60] bg-black/40 backdrop-blur-[2px]"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-label={product.name}
            className="fixed inset-x-0 bottom-0 z-[61] mx-auto max-w-[430px] max-h-[92dvh] overflow-y-auto rounded-t-[1.75rem] bg-white pb-[max(1rem,env(safe-area-inset-bottom))]"
            initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 380, damping: 38 }}
            drag="y" dragConstraints={{ top: 0, bottom: 0 }} dragElastic={{ top: 0, bottom: 0.6 }}
            onDragEnd={(_, i) => { if (i.offset.y > 120 || i.velocity.y > 600) onClose(); }}
          >
            <div className="sticky top-0 z-10 flex justify-center bg-white/90 pt-2.5 pb-1 backdrop-blur">
              <div className="h-1.5 w-10 rounded-full bg-gray-300" />
            </div>
            <button onClick={onClose} className="absolute right-3 top-3 z-20 flex h-9 w-9 items-center justify-center rounded-full bg-gray-100 text-gray-600" aria-label="Cerrar">
              <X className="h-4 w-4" />
            </button>

            <div className="relative mx-auto aspect-square w-[78%] max-w-[300px]">
              {product.image_url ? (
                <Image src={product.image_url} alt={product.name} fill sizes="300px" className="object-contain" priority />
              ) : (
                <div className="flex h-full items-center justify-center text-6xl text-gray-300">🐾</div>
              )}
            </div>

            <div className="space-y-4 px-5 pt-2">
              <div>
                {product.brand && product.brand.toLowerCase() !== 'varios' && (
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">{product.brand}</p>
                )}
                <h2 className="mt-0.5 font-display text-xl font-bold leading-tight text-foreground">{product.name}</h2>
                <div className="mt-2 flex items-center gap-3">
                  <span className="text-2xl font-extrabold tracking-tight">{formatCOP(product.price)}</span>
                  {product.compare_at_price && product.compare_at_price > product.price && (
                    <span className="text-sm text-muted line-through">{formatCOP(product.compare_at_price)}</span>
                  )}
                  {!!product.rating_count && (
                    <span className="ml-auto flex items-center gap-1 text-sm font-semibold">
                      <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                      {product.rating_avg?.toFixed(1)} <span className="font-normal text-muted">({product.rating_count})</span>
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs font-medium text-primary-700">
                  {promesaEntrega()} a Pereira y Dosquebradas · ganas {Math.floor((product.price * qty) / 1000)} puntos
                </p>
              </div>

              {descripcion && <p className="text-sm leading-relaxed text-gray-600">{descripcion}</p>}
              {beneficios.length > 0 && (
                <ul className="space-y-1.5">
                  {beneficios.map((b) => (
                    <li key={b} className="flex gap-2 text-sm text-gray-700">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary-700" />{b}
                    </li>
                  ))}
                </ul>
              )}

              {pets.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">¿Para quién es?</p>
                  <div className="-mx-5 flex gap-2 overflow-x-auto px-5 pb-1 scrollbar-hide">
                    {[{ id: '', name: 'Para la casa', species: '' }, ...pets].map((pet) => (
                      <button
                        key={pet.id || 'casa'}
                        type="button"
                        onClick={() => setPetId(pet.id)}
                        className={`flex shrink-0 items-center gap-1.5 rounded-full border px-3.5 py-2 text-sm font-medium transition-colors ${
                          petId === pet.id ? 'border-primary-700 bg-primary-700 text-white' : 'border-border bg-white text-foreground'
                        }`}
                      >
                        <span>{pet.species ? getSpeciesEmoji(pet.species) : '🏠'}</span>{pet.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="¿Algo que debamos saber? Sabor, talla… (opcional)"
                rows={2}
                className="input-field resize-none"
              />
            </div>

            <div className="sticky bottom-0 mt-4 flex items-center gap-3 border-t border-gray-100 bg-white px-5 pt-3">
              <div className="flex h-12 items-center rounded-full bg-gray-100">
                <button type="button" onClick={() => setQty(Math.max(1, qty - 1))} className="flex h-12 w-11 items-center justify-center" aria-label="Menos">
                  <Minus className="h-4 w-4" />
                </button>
                <span className="w-6 text-center text-base font-bold tabular-nums">{qty}</span>
                <button type="button" onClick={() => setQty(qty + 1)} className="flex h-12 w-11 items-center justify-center" aria-label="Más">
                  <Plus className="h-4 w-4" />
                </button>
              </div>
              <motion.button
                type="button"
                whileTap={{ scale: 0.97 }}
                onClick={agregar}
                disabled={product.in_stock === false}
                className="flex h-12 flex-1 items-center justify-between rounded-full bg-primary-700 px-5 text-sm font-bold text-white shadow-[0_8px_20px_rgba(24,127,119,.3)] disabled:opacity-40"
              >
                <span>{product.in_stock === false ? 'Agotado' : 'Agregar'}</span>
                <span>{formatCOP(product.price * qty)}</span>
              </motion.button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
