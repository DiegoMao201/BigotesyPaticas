'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Search } from 'lucide-react';
import { storeApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

function SearchResults() {
  const params = useSearchParams();
  const q = params.get('q') ?? '';

  const { data, isLoading, isError } = useQuery({
    queryKey: ['buscar', q],
    queryFn: () => storeApi.list({ q, page_size: 48 }),
    enabled: !!q,
    staleTime: 60_000,
  });

  if (!q) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-muted-foreground gap-3">
        <Search className="h-12 w-12 opacity-20" />
        <p className="text-lg">Escribe algo para buscar…</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="rounded-2xl bg-muted/30 animate-pulse h-64" />
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return (
      <p className="text-center py-12 text-muted-foreground">
        Error buscando. Intenta de nuevo.
      </p>
    );
  }

  if (data.items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-muted-foreground gap-3">
        <Search className="h-12 w-12 opacity-20" />
        <p className="text-lg">Sin resultados para <strong>"{q}"</strong></p>
        <p className="text-sm">Prueba con otras palabras o navega por categorías.</p>
      </div>
    );
  }

  return (
    <>
      <p className="text-sm text-muted-foreground mb-6">
        {data.total} resultados para <strong>"{q}"</strong>
      </p>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {data.items.map((p) => (
          <Link
            key={p.id}
            href={`/producto/${p.slug}`}
            className="group rounded-2xl border border-border bg-card hover:border-brand/30 hover:shadow-elegant transition-all overflow-hidden"
          >
            <div className="aspect-square bg-muted/20 flex items-center justify-center overflow-hidden relative">
              {p.primary_image_url ? (
                <img
                  src={p.primary_image_url}
                  alt={p.name}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
              ) : (
                <span className="text-5xl">📦</span>
              )}
              <div className={`absolute top-2 left-2 text-xs font-medium px-2 py-0.5 rounded-full ${
                p.in_stock
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-gray-100 text-gray-500'
              }`}>
                {p.in_stock ? 'Disponible' : 'No disponible'}
              </div>
            </div>
            <div className="p-3 space-y-1">
              <h3 className="font-medium text-sm leading-tight line-clamp-2">{p.name}</h3>
              <p className="font-bold text-brand-700">{formatCurrency(Number(p.price))}</p>
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}

export default function BuscarPage() {
  return (
    <main className="container-wide py-10">
      <h1 className="text-2xl font-display font-bold mb-6">Resultados de búsqueda</h1>
      <Suspense fallback={
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="rounded-2xl bg-muted/30 animate-pulse h-64" />
          ))}
        </div>
      }>
        <SearchResults />
      </Suspense>
    </main>
  );
}
