'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight } from 'lucide-react';
import { orders, pets as petsApi } from '@/lib/api';
import { ProductCard, ProductCardSkeleton } from './ProductCard';
import { ProductSheet } from './ProductSheet';
import { toShop, type ShopProduct } from './types';
import { promesaEntrega } from './entrega';

const ESPECIE: Record<string, string> = { perro: 'dog', dog: 'dog', gato: 'cat', cat: 'cat' };

/**
 * La tienda en el inicio (8-nov-2026). El inicio del portal no mostraba un solo
 * producto: puntos, banners y accesos. Ahora lo primero que se puede tocar es lo que
 * el cliente suele comprar y lo que le sirve a su mascota, con el "+" ahí mismo.
 */
export function DashboardShop() {
  const [abierto, setAbierto] = useState<ShopProduct | null>(null);
  const { data: misPets = [] } = useQuery({ queryKey: ['portal-pets'], queryFn: petsApi.list });
  const { data: top = [] } = useQuery({ queryKey: ['top-products'], queryFn: () => orders.topProducts(8), staleTime: 5 * 60 * 1000 });

  const especies = useMemo(
    () => Array.from(new Set(misPets.map((p) => ESPECIE[p.species?.toLowerCase()] ?? '').filter(Boolean))),
    [misPets],
  );
  const petType = especies.length === 1 ? especies[0] : null;

  const { data: sugeridos = [], isLoading } = useQuery({
    queryKey: ['inicio-sugeridos', petType],
    queryFn: async () => {
      const qs = new URLSearchParams({ in_stock: 'true', page_size: '12', sort: 'relevance' });
      if (petType) qs.set('pet_type', petType);
      const r = await fetch(`/api/v1/products/catalog?${qs}`);
      return r.ok ? ((await r.json()).items as Record<string, unknown>[]).map(toShop) : [];
    },
    staleTime: 5 * 60 * 1000,
  });

  const repetir = top.filter((p) => p.image_url && !/baño|peluquer/i.test(p.name)).map((p) => toShop(p as unknown as Record<string, unknown>));
  const ids = new Set(repetir.map((p) => p.id));
  const lista = [...repetir, ...sugeridos.filter((p) => p.image_url && !ids.has(p.id))].slice(0, 12);
  const nombre = misPets.length === 1 ? misPets[0].name : null;

  return (
    <section className="mt-1">
      <div className="mb-2.5 flex items-end justify-between">
        <div>
          <h2 className="font-display text-[17px] font-bold leading-tight text-foreground">
            {nombre ? `Para ${nombre}` : 'Para tu mascota'}
          </h2>
          <p className="text-xs text-muted">Domicilio gratis · {promesaEntrega()}</p>
        </div>
        <Link href="/orders/new" className="flex items-center gap-0.5 text-sm font-semibold text-primary-700">
          Ver tienda <ChevronRight className="h-4 w-4" />
        </Link>
      </div>
      <div className="-mx-4 flex gap-3 overflow-x-auto px-4 pb-2 scrollbar-hide">
        {isLoading && lista.length === 0
          ? Array.from({ length: 3 }).map((_, i) => <div key={i} className="w-[150px] shrink-0"><ProductCardSkeleton /></div>)
          : lista.map((p) => (
              <div key={p.id} className="w-[150px] shrink-0">
                <ProductCard p={p} onOpen={setAbierto} />
              </div>
            ))}
      </div>
      <ProductSheet
        product={abierto}
        pets={misPets.map((p) => ({ id: p.id, name: p.name, species: p.species }))}
        onClose={() => setAbierto(null)}
      />
    </section>
  );
}
