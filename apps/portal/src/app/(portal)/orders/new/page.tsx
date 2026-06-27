'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { Search, ShoppingCart, Loader2, Star, ChevronDown, ChevronUp, Share2 } from 'lucide-react';
import Image from 'next/image';
import { orders, pets, catalog, auth, referral as referralApi, type PublicProduct, type Pet, type TopProduct } from '@/lib/api';
import { formatCOP, getSpeciesEmoji } from '@/lib/utils';
import { cn } from '@/lib/utils';
import { usePortalCart } from '@/lib/cart-store';

const CATEGORY_ICONS: Record<string, string> = {
  concentrado: '🥘',
  snack: '🍪',
  snacks: '🍪',
  accesorios: '🎾',
  juguetes: '🎾',
  aseo: '💧',
  arena: '🏖️',
  arenas: '🏖️',
  medicamento: '💊',
  perros: '🐶',
  gatos: '🐱',
};
function categoryIcon(slug: string) {
  return CATEGORY_ICONS[slug?.toLowerCase()] ?? '📦';
}

export default function NewOrderPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const addItemToCart = usePortalCart((s) => s.addItem);

  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<PublicProduct | TopProduct | null>(null);
  const [selectedPetId, setSelectedPetId] = useState<string>('');
  const [qty, setQty] = useState(1);
  const [notes, setNotes] = useState('');
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [activeCategoryId, setActiveCategoryId] = useState<string | null>(null);

  const { data: me } = useQuery({ queryKey: ['portal-me'], queryFn: auth.me });
  const { data: petsData } = useQuery({ queryKey: ['portal-pets'], queryFn: pets.list });
  const { data: topProducts = [], isLoading: topLoading } = useQuery({
    queryKey: ['top-products'],
    queryFn: () => orders.topProducts(5),
    staleTime: 5 * 60 * 1000,
  });

  // Categorías del catálogo
  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => fetch('/api/v1/categories').then((r) => r.json()) as Promise<Array<{ id: string; name: string; slug: string }>>,
    staleTime: 60 * 60 * 1000,
    enabled: catalogOpen,
  });

  // Productos filtrados por búsqueda o categoría
  const searchActive = search.length > 0 || activeCategoryId !== null;
  const { data: catalogData, isLoading: catalogLoading } = useQuery({
    queryKey: ['catalog-products', search, activeCategoryId],
    queryFn: () => catalog.list(search || undefined, activeCategoryId ?? undefined),
    staleTime: 60 * 1000,
    enabled: searchActive,
  });
  const filteredProducts = catalogData?.items ?? [];

  const { mutate: createOrder, isPending } = useMutation({
    mutationFn: () => {
      const prod = selected as any;
      return orders.create({
        product_id: prod.id,
        pet_id: selectedPetId || undefined,
        quantity: qty,
        notes: notes || undefined,
      });
    },
    onSuccess: (order) => {
      qc.invalidateQueries({ queryKey: ['portal-orders'] });
      toast.success(
        order.points_earned
          ? `Pedido enviado ✓ +${order.points_earned} puntos`
          : 'Pedido enviado con éxito',
      );
      router.replace('/orders');
    },
    onError: (err: any) => toast.error(err.message ?? 'Error al enviar pedido'),
  });

  const selectedPrice = (selected as any)?.price ?? 0;

  function shareWhatsApp() {
    const code = me?.referral_code;
    if (!code) return;
    const name = me?.full_name?.split(' ')[0] ?? 'tu amigo';
    const msg = encodeURIComponent(
      `¡Hola! 🐾 Te recomiendo Bigotes y Paticas.\nUsa mi código *${code}* al registrarte y los dos ganamos puntos 🎁\n👉 https://mi.bigotesypaticas.com/?ref=${code}`
    );
    window.open(`https://wa.me/?text=${msg}`, '_blank');
  }

  function selectProduct(prod: PublicProduct | TopProduct) {
    setSelected(prod);
    setQty(1);
    setNotes('');
  }

  function addToCart(prod: PublicProduct | TopProduct) {
    addItemToCart({
      product_id: prod.id,
      sku: (prod as TopProduct).sku ?? '',
      name: prod.name,
      image_url: prod.image_url ?? null,
      unit_price: prod.price,
      quantity: 1,
    });
    toast.success('Producto agregado al carrito 🛒');
  }

  if (selected) {
    return (
      <div className="p-4 pt-6 flex flex-col gap-5">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSelected(null)}
            className="p-2 -ml-2 rounded-xl hover:bg-gray-100"
          >
            ← Volver
          </button>
          <h1 className="font-display text-xl font-bold">Confirmar pedido</h1>
        </div>

        <div className="card flex items-center gap-4 py-3 border-2 border-primary-700">
          <div className="h-14 w-14 rounded-xl bg-primary-50 flex items-center justify-center text-2xl shrink-0 overflow-hidden">
            {(selected as any).image_url ? (
              <Image
                src={(selected as any).image_url}
                alt={(selected as any).name}
                width={56}
                height={56}
                className="h-full w-full object-contain p-1"
              />
            ) : (
              '📦'
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-sm">{(selected as any).name}</p>
            <p className="font-bold text-primary-700">{formatCOP(selectedPrice)}</p>
          </div>
          <button onClick={() => setSelected(null)} className="text-xs text-muted underline">
            Cambiar
          </button>
        </div>

        <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 rounded-xl px-4 py-2.5">
          <Star className="h-4 w-4 fill-amber-500 text-amber-500" />
          <span>
            Ganarás <strong>{Math.floor((selectedPrice * qty) / 1_000)} puntos</strong> con este
            pedido
          </span>
        </div>

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
                    : 'border-border text-muted',
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
                      : 'border-border text-muted',
                  )}
                >
                  <span className="text-xl">{getSpeciesEmoji(pet.species)}</span>
                  <span className="truncate w-12 text-center">{pet.name}</span>
                </button>
              ))}
            </div>
          </div>
        )}

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
            <span className="font-bold text-2xl w-8 text-center">{qty}</span>
            <button
              type="button"
              onClick={() => setQty(qty + 1)}
              className="h-10 w-10 rounded-xl border-2 border-primary-700 bg-primary-50 flex items-center justify-center text-xl font-bold text-primary-700"
            >
              +
            </button>
            <span className="text-muted text-sm ml-2">= {formatCOP(selectedPrice * qty)}</span>
          </div>
        </div>

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

        <button onClick={() => createOrder()} disabled={isPending} className="btn-primary">
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
          Un asesor confirmará y coordinará la entrega por WhatsApp.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      {/* Header teal */}
      <div className="bg-primary-700 px-5 pt-8 pb-6 text-white">
        <h1 className="font-display text-2xl font-bold">¿Qué quieres pedir hoy?</h1>
        <p className="text-primary-100 text-sm mt-1">Lo que más compras está aquí abajo</p>
      </div>

      <div className="px-4 pt-4 flex flex-col gap-5 pb-8">
        {/* Banner invitar */}
        {me?.referral_code && (
          <div className="flex items-center gap-3 rounded-2xl px-4 py-3"
            style={{ backgroundColor: '#f5a641' }}>
            <span className="text-2xl">⭐</span>
            <div className="flex-1 min-w-0">
              <p className="font-bold text-white text-sm">Invita amigos · Gana 100 pts</p>
              <p className="text-amber-100 text-xs truncate">
                Comparte tu código {me.referral_code} por WhatsApp
              </p>
            </div>
            <button
              onClick={shareWhatsApp}
              className="bg-white text-amber-700 font-bold text-xs px-3 py-1.5 rounded-xl shrink-0 flex items-center gap-1.5"
            >
              <Share2 className="h-3.5 w-3.5" />
              Compartir
            </button>
          </div>
        )}

        {/* Top 5 */}
        {(topLoading || topProducts.length > 0) && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-display font-bold text-foreground">
                ⚡ Tu top 5 · pide directo
              </h2>
              <span className="text-xs text-muted">basado en tu historial</span>
            </div>
            <div className="flex gap-3 overflow-x-auto scrollbar-hide pb-2 -mx-4 px-4">
              {topLoading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <div
                      key={i}
                      className="min-w-[130px] h-[170px] rounded-2xl bg-gray-100 animate-pulse shrink-0"
                    />
                  ))
                : topProducts.map((prod) => (
                    <motion.button
                      key={prod.id}
                      whileTap={{ scale: 0.96 }}
                      onClick={() => selectProduct(prod as any)}
                      className="min-w-[130px] flex flex-col rounded-2xl border border-border bg-white shadow-sm overflow-hidden shrink-0 text-left hover:shadow-card-hover transition-shadow"
                    >
                      <div className="h-20 bg-gray-50 flex items-center justify-center overflow-hidden">
                        {prod.image_url ? (
                          <Image
                            src={prod.image_url}
                            alt={prod.name}
                            width={80}
                            height={80}
                            className="h-full w-full object-contain p-1"
                          />
                        ) : (
                          <span className="text-3xl">📦</span>
                        )}
                      </div>
                      <div className="p-2.5 flex flex-col gap-1 flex-1">
                        <p className="text-xs font-semibold text-foreground leading-tight line-clamp-2">
                          {prod.name}
                        </p>
                        <p className="text-xs font-bold text-primary-700 mt-auto">
                          {formatCOP(prod.price)}
                        </p>
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); addToCart(prod); }}
                          className="text-[10px] font-bold text-teal-700 bg-teal-50 rounded-lg px-2 py-1 text-center mt-1 w-full hover:bg-teal-100"
                        >
                          🛒 Carrito
                        </button>
                      </div>
                    </motion.button>
                  ))}
            </div>
          </div>
        )}

        {/* Búsqueda */}
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
          <input
            className="input-field pl-10"
            placeholder="¿Buscas algo específico? Escribe el nombre del producto..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setActiveCategoryId(null);
            }}
          />
        </div>

        {/* Resultados de búsqueda */}
        <AnimatePresence>
          {searchActive && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex flex-col gap-2"
            >
              {catalogLoading && (
                <div className="flex justify-center py-4">
                  <div className="h-6 w-6 rounded-full border-2 border-primary-200 border-t-primary-700 animate-spin" />
                </div>
              )}
              {filteredProducts.map((product, i) => (
                <motion.button
                  key={product.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  onClick={() => selectProduct(product)}
                  className="card flex items-center gap-4 py-3 text-left hover:shadow-card-hover transition-shadow active:scale-[0.98]"
                >
                  <div className="h-12 w-12 rounded-xl bg-primary-50 flex items-center justify-center text-2xl shrink-0 overflow-hidden">
                    {product.image_url ? (
                      <Image
                        src={product.image_url}
                        alt={product.name}
                        width={48}
                        height={48}
                        className="h-full w-full object-contain p-1"
                      />
                    ) : (
                      '📦'
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm leading-snug">{product.name}</p>
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
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); addToCart(product); }}
                      className="text-xs text-teal-700 font-semibold bg-teal-50 rounded-lg px-2 py-1 hover:bg-teal-100 transition"
                    >
                      🛒 Carrito
                    </button>
                  </div>
                </motion.button>
              ))}
              {!catalogLoading && filteredProducts.length === 0 && (
                <div className="text-center py-6 text-muted">
                  <p className="text-2xl mb-2">🔍</p>
                  <p className="text-sm">Sin resultados. Prueba con otro término.</p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Portafolio completo — colapsado por defecto */}
        {!searchActive && (
          <div className="rounded-2xl border border-border overflow-hidden">
            <button
              onClick={() => setCatalogOpen(!catalogOpen)}
              className="w-full flex items-center gap-3 px-4 py-4 bg-gray-50 hover:bg-gray-100 transition-colors"
            >
              <span className="text-2xl">📚</span>
              <div className="text-left flex-1">
                <p className="font-bold text-foreground text-sm">Ver portafolio completo</p>
                <p className="text-xs text-muted">Explora por categorías · 247 productos</p>
              </div>
              {catalogOpen ? (
                <ChevronUp className="h-5 w-5 text-muted" />
              ) : (
                <ChevronDown className="h-5 w-5 text-primary-700" />
              )}
            </button>

            <AnimatePresence>
              {catalogOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="p-3 border-t border-border">
                    {/* Grid de categorías */}
                    <div className="grid grid-cols-2 gap-2 mb-3">
                      {categoriesData
                        ?.filter((c) => !['sin-categoria'].includes(c.slug))
                        .map((cat) => (
                          <button
                            key={cat.id}
                            onClick={() => {
                              setActiveCategoryId(cat.id);
                              setCatalogOpen(false);
                            }}
                            className="flex items-center gap-2.5 rounded-xl border border-border px-3 py-3 bg-white hover:bg-primary-50 hover:border-primary-300 transition-colors text-left"
                          >
                            <span className="text-xl">{categoryIcon(cat.slug)}</span>
                            <span className="text-sm font-semibold text-foreground capitalize">
                              {cat.name.charAt(0).toUpperCase() + cat.name.slice(1).toLowerCase()}
                            </span>
                          </button>
                        ))}
                    </div>
                    <p className="text-xs text-muted text-center italic">
                      Al tocar una categoría verás todos sus productos
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}
