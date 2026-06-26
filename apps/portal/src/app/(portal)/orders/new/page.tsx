'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { ArrowLeft, Search, ShoppingCart, Loader2, Star } from 'lucide-react';
import Image from 'next/image';
import { orders, pets, catalog, type PublicProduct, type Pet } from '@/lib/api';
import { formatCOP, getSpeciesEmoji } from '@/lib/utils';
import { cn } from '@/lib/utils';

export default function NewOrderPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<PublicProduct | null>(null);
  const [selectedPetId, setSelectedPetId] = useState<string>('');
  const [qty, setQty] = useState(1);
  const [notes, setNotes] = useState('');

  const { data: petsData } = useQuery({
    queryKey: ['portal-pets'],
    queryFn: pets.list,
  });

  // Filtrar productos por búsqueda — NUNCA mostramos stock
  const { data: catalogData, isLoading: catalogLoading } = useQuery({
    queryKey: ['catalog-products', search],
    queryFn: () => catalog.list(search || undefined),
    staleTime: 60 * 1000,
  });

  const products = catalogData?.items ?? [];

  const { mutate: createOrder, isPending } = useMutation({
    mutationFn: () =>
      orders.create({
        product_id: selected!.id,
        pet_id: selectedPetId || undefined,
        quantity: qty,
        notes: notes || undefined,
      }),
    onSuccess: (order) => {
      qc.invalidateQueries({ queryKey: ['portal-orders'] });
      toast.success(
        order.points_earned
          ? `Pedido enviado ✓ +${order.points_earned} puntos`
          : 'Pedido enviado con éxito'
      );
      router.replace('/orders');
    },
    onError: (err: any) => toast.error(err.message ?? 'Error al enviar pedido'),
  });

  return (
    <div className="p-4 pt-6 flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="p-2 -ml-2 rounded-xl hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h1 className="font-display text-xl font-bold text-foreground">Nuevo pedido</h1>
      </div>

      {/* Búsqueda de producto */}
      {!selected && (
        <>
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
            <input
              className="input-field pl-10"
              placeholder="Buscar producto, alimento, accesorio..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
          </div>

          {catalogLoading && (
            <div className="flex justify-center py-6">
              <div className="h-6 w-6 rounded-full border-2 border-primary-200 border-t-primary-700 animate-spin" />
            </div>
          )}

          <div className="flex flex-col gap-2">
            {products.map((product, i) => (
              <motion.button
                key={product.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                onClick={() => setSelected(product)}
                className="card flex items-center gap-4 py-3 text-left hover:shadow-card-hover transition-shadow active:scale-[0.98]"
              >
                <div className="h-14 w-14 rounded-xl bg-primary-50 flex items-center justify-center text-2xl shrink-0 overflow-hidden">
                  {product.image_url ? (
                    <Image src={product.image_url} alt={product.name} width={56} height={56} className="h-full w-full object-cover" />
                  ) : (
                    '📦'
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-foreground text-sm leading-snug">{product.name}</p>
                  {product.category && (
                    <p className="text-xs text-muted">
                      {typeof product.category === 'object'
                        ? (product.category as { name: string })?.name
                        : product.category}
                    </p>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <p className="font-bold text-primary-700 text-sm">{formatCOP(product.price)}</p>
                  {/* NUNCA mostramos stock — siempre "Pedir" */}
                  <span className="text-xs text-green-600 font-semibold">Disponible</span>
                </div>
              </motion.button>
            ))}

            {!catalogLoading && products.length === 0 && (
              <div className="text-center py-8 text-muted">
                <p className="text-2xl mb-2">🔍</p>
                <p className="text-sm">Sin resultados. Prueba con otro término.</p>
              </div>
            )}
          </div>
        </>
      )}

      {/* Detalle del pedido */}
      {selected && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-5"
        >
          {/* Producto seleccionado */}
          <div className="card flex items-center gap-4 py-3 border-2 border-primary-700">
            <div className="h-14 w-14 rounded-xl bg-primary-50 flex items-center justify-center text-2xl shrink-0 overflow-hidden">
              {selected.image_url ? (
                <Image src={selected.image_url} alt={selected.name} width={56} height={56} className="h-full w-full object-cover" />
              ) : '📦'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-foreground text-sm">{selected.name}</p>
              <p className="font-bold text-primary-700">{formatCOP(selected.price)}</p>
            </div>
            <button
              onClick={() => setSelected(null)}
              className="text-xs text-muted underline"
            >
              Cambiar
            </button>
          </div>

          {/* Puntos que ganará */}
          <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 rounded-xl px-4 py-2.5">
            <Star className="h-4 w-4 fill-amber-500 text-amber-500" />
            <span>Ganarás <strong>{Math.floor((selected.price * qty) / 1_000)} puntos</strong> con este pedido</span>
          </div>

          {/* Mascota */}
          {petsData && petsData.length > 0 && (
            <div>
              <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-2 block">
                Para qué mascota (opcional)
              </label>
              <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-1">
                <button
                  onClick={() => setSelectedPetId('')}
                  className={cn(
                    'flex flex-col items-center gap-1.5 min-w-[60px] px-3 py-2 rounded-xl border-2 text-xs font-medium transition-all',
                    !selectedPetId
                      ? 'border-primary-700 bg-primary-50 text-primary-700'
                      : 'border-border text-muted'
                  )}
                >
                  <span className="text-xl">👥</span>
                  General
                </button>
                {petsData.map((pet) => (
                  <button
                    key={pet.id}
                    onClick={() => setSelectedPetId(pet.id)}
                    className={cn(
                      'flex flex-col items-center gap-1.5 min-w-[60px] px-3 py-2 rounded-xl border-2 text-xs font-medium transition-all',
                      selectedPetId === pet.id
                        ? 'border-primary-700 bg-primary-50 text-primary-700'
                        : 'border-border text-muted'
                    )}
                  >
                    <span className="text-xl">{getSpeciesEmoji(pet.species)}</span>
                    <span className="truncate w-12 text-center">{pet.name}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Cantidad */}
          <div>
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-2 block">
              Cantidad
            </label>
            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={() => setQty(Math.max(1, qty - 1))}
                className="h-10 w-10 rounded-xl border-2 border-border flex items-center justify-center text-xl font-bold"
              >
                −
              </button>
              <span className="font-bold text-2xl text-foreground w-8 text-center">{qty}</span>
              <button
                type="button"
                onClick={() => setQty(qty + 1)}
                className="h-10 w-10 rounded-xl border-2 border-primary-700 bg-primary-50 flex items-center justify-center text-xl font-bold text-primary-700"
              >
                +
              </button>
              <span className="text-muted text-sm ml-2">= {formatCOP(selected.price * qty)}</span>
            </div>
          </div>

          {/* Notas */}
          <div>
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-2 block">
              Notas adicionales
            </label>
            <textarea
              className="input-field min-h-[72px] resize-none"
              placeholder="Sabor, presentación, indicaciones especiales..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          {/* Botón enviar */}
          <button
            onClick={() => createOrder()}
            disabled={isPending}
            className="btn-primary"
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <ShoppingCart className="h-4 w-4" />
                Enviar pedido
              </>
            )}
          </button>

          <p className="text-xs text-muted text-center">
            Un asesor confirmará disponibilidad y coordinará la entrega por WhatsApp.
          </p>
        </motion.div>
      )}
    </div>
  );
}
