'use client';

import { useState, useMemo, useCallback } from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronDown, Heart, MessageCircle } from 'lucide-react';
import { formatCurrency } from '@/lib/utils';
import type { Product } from '@/lib/api';
import { getOutOfStockWhatsAppUrl } from '@/lib/whatsapp-messages';

export interface FilterChip {
  label: string;
  keyword: string;
  /** Si se define, el chip filtra server-side via ?sub_cat=slug en lugar de client-side */
  categorySlug?: string;
}

interface CatalogGridProps {
  initialItems: Product[];
  totalCount: number;
  /** URLSearchParams string para cargar más páginas, ej: "species=perro&is_published=true" */
  apiQuery: string;
  filterChips?: FilterChip[];
  slug: string;
  /** pet_type activo de la página (dog/cat) para filtros de chips client-side */
  petType?: string;
}

type SortKey = 'relevance' | 'price_asc' | 'price_desc';

const PER_PAGE = 40;

export function CatalogGrid({ initialItems, totalCount, apiQuery, filterChips = [], slug, petType }: CatalogGridProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [items, setItems] = useState<Product[]>(initialItems);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState('');
  const [sort, setSort] = useState<SortKey>('relevance');

  // Estado client-side para chips de categoría (fetch instantáneo, sin server re-render)
  const [activeSubCat, setActiveSubCat] = useState(searchParams.get('sub_cat') ?? '');
  const [chipItems, setChipItems] = useState<Product[] | null>(null);
  const [chipTotal, setChipTotal] = useState<number | null>(null);
  const [chipLoading, setChipLoading] = useState(false);

  const effectiveItems = chipItems ?? items;
  const effectiveTotal = chipTotal ?? totalCount;
  const hasMore = effectiveItems.length < effectiveTotal && !chipLoading;

  const loadMore = useCallback(async () => {
    setLoading(true);
    try {
      const nextPage = page + 1;
      let query: string;
      if (activeSubCat) {
        const qs = new URLSearchParams({ is_published: 'true', page_size: String(PER_PAGE), page: String(nextPage) });
        qs.set('category_slug', activeSubCat);
        if (petType) qs.set('pet_type', petType);
        query = qs.toString();
      } else {
        query = `${apiQuery}&per_page=${PER_PAGE}&page=${nextPage}`;
      }
      const res = await fetch(`/api/v1/products?${query}`);
      if (!res.ok) throw new Error('fetch error');
      const data = await res.json();
      const newItems: Product[] = data.items ?? [];
      if (activeSubCat) {
        setChipItems((prev) => {
          const existingIds = new Set((prev ?? []).map((p) => p.id));
          return [...(prev ?? []), ...newItems.filter((p) => !existingIds.has(p.id))];
        });
      } else {
        setItems((prev) => {
          const existingIds = new Set(prev.map((p) => p.id));
          return [...prev, ...newItems.filter((p: Product) => !existingIds.has(p.id))];
        });
      }
      setPage(nextPage);
    } catch {
      /* silencioso */
    } finally {
      setLoading(false);
    }
  }, [page, apiQuery, activeSubCat, petType]);

  const displayed = useMemo(() => {
    let result = [...effectiveItems];

    // Solo filtro client-side para chips SIN categorySlug (keyword puro)
    if (activeFilter && !activeSubCat) {
      const kw = activeFilter.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(kw) ||
          p.category?.name.toLowerCase().includes(kw) ||
          p.tags?.some((t) => t.toLowerCase().includes(kw))
      );
    }

    if (sort === 'price_asc') result.sort((a, b) => Number(a.price) - Number(b.price));
    if (sort === 'price_desc') result.sort((a, b) => Number(b.price) - Number(a.price));

    return result;
  }, [effectiveItems, activeFilter, activeSubCat, sort]);

  const allChips: FilterChip[] = [{ label: 'Todos', keyword: '', categorySlug: '' }, ...filterChips];

  async function handleChipClick(chip: FilterChip) {
    if (chip.categorySlug !== undefined) {
      // "Todos" — limpiar estado y volver al URL limpio
      if (!chip.categorySlug) {
        setActiveSubCat('');
        setChipItems(null);
        setChipTotal(null);
        setPage(1);
        // Si la página actual tenía sub_cat en URL (cargó filtrado desde servidor),
        // navegar para restablecer los items del servidor
        if (searchParams.get('sub_cat')) {
          router.push(pathname, { scroll: false });
        }
        return;
      }

      // Chip de categoría: fetch client-side INSTANTÁNEO
      setActiveSubCat(chip.categorySlug);
      setChipItems([]);   // mostrar vacío mientras carga
      setChipTotal(null);
      setChipLoading(true);
      setPage(1);

      // Actualizar URL silenciosamente (sin re-render del servidor)
      const newUrl = `${pathname}?sub_cat=${chip.categorySlug}`;
      window.history.pushState(null, '', newUrl);

      try {
        const qs = new URLSearchParams({ is_published: 'true', page_size: String(PER_PAGE) });
        qs.set('category_slug', chip.categorySlug);
        if (petType) qs.set('pet_type', petType);
        const res = await fetch(`/api/v1/products?${qs.toString()}`);
        if (!res.ok) throw new Error('fetch error');
        const data = await res.json();
        setChipItems(data.items ?? []);
        setChipTotal(data.total ?? 0);
      } catch {
        // Fallback a navegación server-side si falla el fetch
        router.push(newUrl, { scroll: false });
      } finally {
        setChipLoading(false);
      }
    } else {
      // Client-side: filtro de texto local (para chips sin categorySlug)
      setActiveFilter(chip.keyword);
    }
  }

  function isChipActive(chip: FilterChip): boolean {
    if (chip.categorySlug !== undefined) {
      return activeSubCat === chip.categorySlug;
    }
    return activeFilter === chip.keyword;
  }

  return (
    <div>
      {/* ── Barra sticky de filtros ── */}
      <div className="sticky top-14 z-30 bg-white/95 backdrop-blur py-2.5 -mx-4 px-4 border-b border-gray-100 mb-6">
        <div className="flex gap-2 overflow-x-auto scrollbar-hide items-center">
          {allChips.map((chip) => (
            <button
              key={chip.label}
              onClick={() => handleChipClick(chip)}
              className={`flex-shrink-0 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all ${
                isChipActive(chip)
                  ? 'bg-[#187f77] text-white shadow-sm'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {chip.label}
            </button>
          ))}

          {/* Sort */}
          <div className="ml-auto flex-shrink-0 relative">
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortKey)}
              className="appearance-none pl-3 pr-7 py-1.5 rounded-full text-xs font-semibold
                         bg-gray-100 text-gray-600 border-0 cursor-pointer focus:outline-none"
            >
              <option value="relevance">Relevancia</option>
              <option value="price_asc">Precio ↑</option>
              <option value="price_desc">Precio ↓</option>
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Contador cuando filtro client-side activo (solo para chips sin categorySlug) */}
      {activeFilter && !activeSubCat && (
        <p className="text-xs text-gray-500 mb-4">
          {displayed.length} resultado{displayed.length !== 1 ? 's' : ''} para &ldquo;
          {allChips.find((c) => c.keyword === activeFilter)?.label}&rdquo;
        </p>
      )}

      {/* Skeleton de carga para chips de categoría */}
      {chipLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3 mb-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="bg-white rounded-2xl border border-gray-100 overflow-hidden animate-pulse">
              <div className="aspect-square bg-gray-100" />
              <div className="p-2.5 space-y-1.5">
                <div className="h-2 bg-gray-100 rounded w-2/3" />
                <div className="h-3 bg-gray-100 rounded" />
                <div className="h-3 bg-gray-100 rounded w-4/5" />
                <div className="h-4 bg-gray-100 rounded w-1/2 mt-1" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!chipLoading && displayed.length > 0 ? (
        <>
          {/* ── Grid ── */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
            {displayed.map((p) => {
              const discount =
                p.compare_at_price && Number(p.compare_at_price) > Number(p.price)
                  ? Math.round((1 - Number(p.price) / Number(p.compare_at_price)) * 100)
                  : null;

              return (
                <Link
                  key={p.id}
                  href={`/producto/${p.slug}`}
                  className="group block relative bg-white rounded-2xl overflow-hidden
                             border border-gray-100 hover:border-[#187f77]/40
                             hover:shadow-lg hover:shadow-black/5
                             transition-all duration-200"
                >
                  {/* Imagen */}
                  <div className="relative aspect-square bg-[#F8F9FA] overflow-hidden">
                    {p.primary_image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={p.primary_image_url}
                        alt={p.name}
                        className={`w-full h-full object-contain p-2.5
                                   group-hover:scale-105 transition-transform duration-300
                                   ${!p.in_stock ? 'grayscale opacity-70' : ''}`}
                      />
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center text-4xl opacity-25">
                        🐾
                      </div>
                    )}

                    {/* Badge stock */}
                    <div className="absolute top-1.5 left-1.5">
                      {p.in_stock ? (
                        <span className="bg-[#187f77] text-white text-[9px] font-bold
                                         px-1.5 py-0.5 rounded-full uppercase tracking-wide">
                          Disponible
                        </span>
                      ) : (
                        <span className="bg-amber-100 text-amber-700 text-[9px] font-bold
                                         px-1.5 py-0.5 rounded-full uppercase tracking-wide border border-amber-200">
                          Agotado · Lo conseguimos
                        </span>
                      )}
                    </div>

                    {/* Badge descuento */}
                    {discount && (
                      <div className="absolute top-1.5 right-1.5">
                        <span className="bg-[#f5a641] text-white text-[9px] font-bold
                                         px-1.5 py-0.5 rounded-full">
                          -{discount}%
                        </span>
                      </div>
                    )}

                    {/* Favorito (hover desktop / siempre móvil) */}
                    <button
                      onClick={(e) => e.preventDefault()}
                      aria-label="Guardar"
                      className="absolute bottom-1.5 right-1.5 w-7 h-7 rounded-full bg-white
                                 shadow-md flex items-center justify-center
                                 opacity-100 sm:opacity-0 sm:group-hover:opacity-100
                                 transition-opacity duration-150"
                    >
                      <Heart className="w-3.5 h-3.5 text-gray-500" />
                    </button>
                  </div>

                  {/* Info compacta */}
                  <div className="p-2.5 space-y-0.5">
                    {(p.category?.name || p.brand?.name) && (
                      <p className="text-[9px] text-gray-400 uppercase tracking-wide truncate">
                        {p.category?.name}
                        {p.brand?.name ? ` · ${p.brand.name}` : ''}
                      </p>
                    )}
                    <h3 className="text-xs font-semibold text-[#0d4a45] line-clamp-2
                                   leading-tight min-h-[2rem]">
                      {p.name}
                    </h3>
                    <div className="flex items-baseline gap-1 pt-0.5">
                      {discount && p.compare_at_price && (
                        <span className="text-[10px] text-gray-400 line-through">
                          {formatCurrency(p.compare_at_price)}
                        </span>
                      )}
                      <span
                        className={`text-sm font-bold ${
                          p.in_stock ? 'text-[#187f77]' : 'text-gray-400'
                        }`}
                      >
                        {formatCurrency(p.price)}
                      </span>
                    </div>
                    {!p.in_stock && (
                      <a
                        href={getOutOfStockWhatsAppUrl({
                          name: p.name,
                          brand: p.brand ? { name: p.brand.name } : null,
                          price: p.price,
                          slug: p.slug,
                        })}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="mt-1 flex items-center justify-center gap-1 w-full py-1 rounded-lg
                                   bg-green-500 hover:bg-green-600 text-white text-[9px] font-bold
                                   transition-colors"
                      >
                        <MessageCircle className="w-2.5 h-2.5" />
                        Lo consigo por WhatsApp
                      </a>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>

          {/* Cargar más */}
          {hasMore && !activeFilter && (
            <div className="flex flex-col items-center mt-10 gap-2">
              <p className="text-xs text-gray-400">
                Mostrando {items.length} de {totalCount} productos
              </p>
              <button
                onClick={loadMore}
                disabled={loading}
                className="px-8 py-3 rounded-full border-2 border-[#187f77]/30
                           text-[#187f77] font-semibold text-sm
                           hover:bg-[#187f77] hover:text-white hover:border-[#187f77]
                           transition-all duration-200 disabled:opacity-50"
              >
                {loading ? 'Cargando...' : 'Cargar más productos →'}
              </button>
            </div>
          )}
        </>
      ) : (
        !chipLoading && (
          <div className="py-16 text-center text-gray-400">
            <p className="text-4xl mb-3">🔍</p>
            <p className="font-semibold text-gray-500">Sin resultados para este filtro</p>
            <button
              onClick={() => handleChipClick({ label: 'Todos', keyword: '', categorySlug: '' })}
              className="mt-3 text-sm text-[#187f77] underline hover:no-underline"
            >
              Ver todos los productos
            </button>
          </div>
        )
      )}
    </div>
  );
}
