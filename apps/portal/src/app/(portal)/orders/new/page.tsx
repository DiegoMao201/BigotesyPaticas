'use client';

/**
 * TIENDA DEL PORTAL (8-nov-2026). Diego: "cliente que entre es cliente que debe volver…
 * competir con apps grandotas como Laika". Lo de antes era un top 5 y un catálogo
 * escondido detrás de un acordeón ("Ver portafolio completo"): para comprar algo que no
 * hubieras comprado antes había que adivinar que existía. Ahora es una tienda de verdad:
 * buscador fijo arriba, la mascota del cliente decide qué se ve primero (perro o gato),
 * categorías en fichas, "Lo de siempre" para repetir en un toque, rejilla de 2 columnas
 * con foto grande y el "+" en la tarjeta, detalle en hoja que sube desde abajo y la barra
 * del carrito siempre a la vista. Solo productos con stock, primero.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Search, X, SlidersHorizontal, RotateCcw } from 'lucide-react';
import { orders, pets as petsApi, catalog } from '@/lib/api';
import { ProductCard, ProductCardSkeleton } from '@/components/shop/ProductCard';
import { ProductSheet } from '@/components/shop/ProductSheet';
import { CartBar } from '@/components/shop/CartBar';
import { toShop, type ShopProduct } from '@/components/shop/types';

const CATEGORIAS: { slug: string; nombre: string; icono: string }[] = [
  { slug: 'alimento-seco', nombre: 'Concentrado', icono: '🥣' },
  { slug: 'snacks', nombre: 'Snacks', icono: '🦴' },
  { slug: 'alimento-medicado', nombre: 'Dietas vet.', icono: '🩺' },
  { slug: 'medicamentos', nombre: 'Salud', icono: '💊' },
  { slug: 'higiene-y-cuidado', nombre: 'Aseo y arena', icono: '🫧' },
  { slug: 'juguetes', nombre: 'Juguetes', icono: '🧸' },
  { slug: 'accesorios', nombre: 'Accesorios', icono: '🎀' },
  { slug: 'alimento-natural', nombre: 'Natural', icono: '🥕' },
];
const ORDEN = [
  { v: 'relevance', l: 'Destacados' },
  { v: 'price_asc', l: 'Menor precio' },
  { v: 'price_desc', l: 'Mayor precio' },
  { v: 'newest', l: 'Nuevos' },
];
const ESPECIE: Record<string, string> = { perro: 'dog', dog: 'dog', gato: 'cat', cat: 'cat' };

function useDebounced<T>(v: T, ms = 300) {
  const [d, setD] = useState(v);
  useEffect(() => { const t = setTimeout(() => setD(v), ms); return () => clearTimeout(t); }, [v, ms]);
  return d;
}

export default function TiendaPage() {
  const [q, setQ] = useState('');
  const qd = useDebounced(q.trim());
  const [cat, setCat] = useState<string | null>(null);
  const [petType, setPetType] = useState<string | null>(null);
  const [orden, setOrden] = useState('relevance');
  const [abierto, setAbierto] = useState<ShopProduct | null>(null);
  const [verOrden, setVerOrden] = useState(false);
  const elegidoPorDefecto = useRef(false);

  const { data: misPets = [] } = useQuery({ queryKey: ['portal-pets'], queryFn: petsApi.list });
  const { data: top = [] } = useQuery({ queryKey: ['top-products'], queryFn: () => orders.topProducts(8), staleTime: 5 * 60 * 1000 });

  // La mascota decide la vitrina: si todas son perros (o todas gatos), se abre filtrada.
  const especies = useMemo(
    () => Array.from(new Set(misPets.map((p) => ESPECIE[p.species?.toLowerCase()] ?? '').filter(Boolean))),
    [misPets],
  );
  useEffect(() => {
    if (!elegidoPorDefecto.current && especies.length === 1) {
      setPetType(especies[0]);
      elegidoPorDefecto.current = true;
    }
  }, [especies]);

  const buscando = qd.length > 1;

  const lista = useInfiniteQuery({
    queryKey: ['tienda', cat, petType, orden],
    enabled: !buscando,
    initialPageParam: 1,
    queryFn: async ({ pageParam }) => {
      const qs = new URLSearchParams({ in_stock: 'true', page: String(pageParam), page_size: '24', sort: orden });
      if (cat) qs.set('category_slug', cat);
      if (petType) qs.set('pet_type', petType);
      const r = await fetch(`/api/v1/products/catalog?${qs}`);
      if (!r.ok) throw new Error('catálogo');
      const d = (await r.json()) as { items: Record<string, unknown>[]; total: number; page: number; page_size: number };
      return { items: d.items.map(toShop), total: d.total, page: d.page, size: d.page_size };
    },
    getNextPageParam: (last) => (last.page * last.size < last.total ? last.page + 1 : undefined),
    staleTime: 2 * 60 * 1000,
  });

  const busqueda = useQuery({
    queryKey: ['tienda-buscar', qd],
    enabled: buscando,
    queryFn: () => catalog.list(qd).then((r) => r.items.map((p) => toShop(p as unknown as Record<string, unknown>))),
    staleTime: 60 * 1000,
  });

  const productos = buscando ? busqueda.data ?? [] : lista.data?.pages.flatMap((p) => p.items) ?? [];
  const total = buscando ? productos.length : lista.data?.pages[0]?.total ?? 0;
  const cargando = buscando ? busqueda.isLoading : lista.isLoading;

  // Carga la siguiente página al acercarse al final, sin botón.
  const centinela = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = centinela.current;
    if (!el || buscando) return;
    const io = new IntersectionObserver((e) => {
      if (e[0].isIntersecting && lista.hasNextPage && !lista.isFetchingNextPage) lista.fetchNextPage();
    }, { rootMargin: '600px' });
    io.observe(el);
    return () => io.disconnect();
  }, [buscando, lista]);

  const nombreMascota = misPets.length === 1 ? misPets[0].name : null;
  // Solo productos con foto: un servicio (baño) o una paleta sin foto en la primera
  // fila de la tienda se ven como error.
  const repetir = top.filter((p) => p.image_url && !/baño|peluquer/i.test(p.name));
  const mostrarRepetir = !buscando && !cat && repetir.length > 0;

  return (
    <div className="min-h-[100dvh] bg-[#f6f7f5] pb-40">
      {/* Cabecera fija con buscador */}
      <div className="sticky top-0 z-30 bg-[#f6f7f5]/90 px-4 pb-3 pt-[max(1rem,env(safe-area-inset-top))] backdrop-blur-xl">
        <div className="mb-3 flex items-end justify-between pr-12">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary-700">Tienda</p>
            <h1 className="font-display text-[26px] font-extrabold leading-tight tracking-tight text-foreground">
              {nombreMascota ? `Lo mejor para ${nombreMascota}` : '¿Qué necesita tu mascota?'}
            </h1>
          </div>
        </div>
        <div className="relative">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-gray-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Busca concentrado, arena, Churu…"
            inputMode="search"
            className="h-12 w-full rounded-2xl border-0 bg-white pl-11 pr-10 text-[15px] shadow-[0_1px_2px_rgba(16,24,40,.05),0_2px_10px_rgba(16,24,40,.05)] outline-none ring-1 ring-black/5 placeholder:text-gray-400 focus:ring-2 focus:ring-primary-700/40"
          />
          {q && (
            <button onClick={() => setQ('')} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full bg-gray-200 p-1" aria-label="Borrar búsqueda">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {!buscando && (
          <div className="-mx-4 mt-3 flex gap-2 overflow-x-auto px-4 scrollbar-hide">
            {[{ v: null as string | null, l: 'Todo', e: '✨' }, { v: 'dog', l: 'Perros', e: '🐶' }, { v: 'cat', l: 'Gatos', e: '🐱' }].map((o) => (
              <button
                key={o.l}
                onClick={() => setPetType(o.v)}
                className={`flex shrink-0 items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
                  petType === o.v ? 'bg-gray-900 text-white' : 'bg-white text-gray-700 ring-1 ring-black/5'
                }`}
              >
                <span>{o.e}</span>{o.l}
              </button>
            ))}
            <button
              onClick={() => setVerOrden((v) => !v)}
              className="ml-auto flex shrink-0 items-center gap-1.5 rounded-full bg-white px-3.5 py-2 text-sm font-semibold text-gray-700 ring-1 ring-black/5"
            >
              <SlidersHorizontal className="h-4 w-4" />{ORDEN.find((o) => o.v === orden)?.l}
            </button>
          </div>
        )}
        {verOrden && !buscando && (
          <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} className="mt-2 flex flex-wrap gap-2">
            {ORDEN.map((o) => (
              <button key={o.v} onClick={() => { setOrden(o.v); setVerOrden(false); }}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ${orden === o.v ? 'bg-primary-700 text-white' : 'bg-white text-gray-700 ring-1 ring-black/5'}`}>
                {o.l}
              </button>
            ))}
          </motion.div>
        )}
      </div>

      {/* Categorías */}
      {!buscando && (
        <div className="-mt-1 grid grid-cols-4 gap-2 px-4 pb-1 pt-1">
          {CATEGORIAS.map((c) => {
            const activa = cat === c.slug;
            return (
              <motion.button
                key={c.slug}
                whileTap={{ scale: 0.94 }}
                onClick={() => setCat(activa ? null : c.slug)}
                className={`flex flex-col items-center gap-1 rounded-2xl px-1 py-2.5 transition-colors ${
                  activa ? 'bg-primary-700 text-white shadow-[0_6px_16px_rgba(24,127,119,.3)]' : 'bg-white text-gray-700 ring-1 ring-black/5'
                }`}
              >
                <span className="text-[22px] leading-none">{c.icono}</span>
                <span className="text-[11px] font-semibold leading-tight">{c.nombre}</span>
              </motion.button>
            );
          })}
        </div>
      )}

      {/* Lo de siempre */}
      {mostrarRepetir && (
        <section className="mt-5">
          <div className="mb-2.5 flex items-center justify-between px-4">
            <h2 className="flex items-center gap-1.5 font-display text-[17px] font-bold">
              <RotateCcw className="h-4 w-4 text-primary-700" /> Lo de siempre
            </h2>
            <span className="text-xs text-muted">un toque y listo</span>
          </div>
          <div className="-mb-2 flex gap-3 overflow-x-auto px-4 pb-2 scrollbar-hide">
            {repetir.map((p) => (
              <div key={p.id} className="w-[150px] shrink-0">
                <ProductCard p={toShop(p as unknown as Record<string, unknown>)} onOpen={setAbierto} />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Rejilla */}
      <section className="mt-5 px-4">
        <div className="mb-2.5 flex items-baseline justify-between">
          <h2 className="font-display text-[17px] font-bold">
            {buscando ? `Resultados para “${qd}”` : cat ? CATEGORIAS.find((c) => c.slug === cat)?.nombre : 'Todo con stock'}
          </h2>
          {!cargando && <span className="text-xs text-muted">{total} productos</span>}
        </div>

        <div className="grid grid-cols-2 gap-3">
          {cargando
            ? Array.from({ length: 6 }).map((_, i) => <ProductCardSkeleton key={i} />)
            : productos.map((p, i) => (
                <motion.div
                  key={p.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.28, delay: Math.min(i % 24, 8) * 0.03, ease: [0.22, 1, 0.36, 1] }}
                >
                  <ProductCard p={p} onOpen={setAbierto} />
                </motion.div>
              ))}
          {lista.isFetchingNextPage && Array.from({ length: 2 }).map((_, i) => <ProductCardSkeleton key={`m${i}`} />)}
        </div>

        {!cargando && productos.length === 0 && (
          <div className="flex flex-col items-center py-14 text-center">
            <span className="text-5xl">🔎</span>
            <p className="mt-3 font-semibold">No encontramos eso</p>
            <p className="mt-1 max-w-[260px] text-sm text-muted">Prueba con la marca o escríbenos por WhatsApp: si no lo tenemos, te lo conseguimos.</p>
          </div>
        )}
        <div ref={centinela} className="h-4" />
      </section>

      <ProductSheet
        product={abierto}
        pets={misPets.map((p) => ({ id: p.id, name: p.name, species: p.species }))}
        onClose={() => setAbierto(null)}
      />
      <CartBar />
    </div>
  );
}
