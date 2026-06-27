'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Search, MessageCircle } from 'lucide-react';
import { storeApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { getWhatsAppUrl } from '@/lib/whatsapp-messages';

function SearchResults() {
  const params = useSearchParams();
  const q = params.get('q') ?? '';

  const { data, isLoading, isError } = useQuery({
    queryKey: ['buscar', q],
    queryFn: () => storeApi.list({ q, per_page: 48 }),
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
    const waUrl = getWhatsAppUrl(
      `¡Hola! Busqué "${q}" en su sitio web y no encontré resultados. ¿Tienen algo similar disponible?`
    );
    return (
      <div className="flex flex-col items-center justify-center py-24 text-muted-foreground gap-4 text-center">
        <Search className="h-14 w-14 opacity-20" />
        <div>
          <p className="text-xl font-semibold text-foreground">Sin resultados para &ldquo;{q}&rdquo;</p>
          <p className="text-sm mt-1">Intenta con otra palabra o escríbenos por WhatsApp.</p>
        </div>
        <a
          href={waUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-green-500 hover:bg-green-600 text-white font-semibold text-sm transition-colors"
        >
          <MessageCircle className="h-4 w-4" />
          Buscar por WhatsApp
        </a>
        <div className="mt-4 flex flex-wrap gap-2 justify-center">
          {['Perros', 'Gatos', 'Accesorios', 'Snacks'].map((cat) => (
            <Link
              key={cat}
              href={`/categorias/${cat.toLowerCase()}`}
              className="px-3 py-1.5 rounded-full border border-border text-sm hover:bg-secondary transition-colors"
            >
              {cat}
            </Link>
          ))}
        </div>
      </div>
    );
  }

  return (
    <>
      <p className="text-sm text-muted-foreground mb-6">
        {data.total} resultado{data.total !== 1 ? 's' : ''} para <strong>&ldquo;{q}&rdquo;</strong>
      </p>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {data.items.map((p) => (
          <Link
            key={p.id}
            href={`/producto/${p.slug}`}
            className="group rounded-2xl border border-border bg-card hover:border-brand/30 hover:shadow-elegant transition-all overflow-hidden"
          >
            <div className="aspect-square bg-white flex items-center justify-center overflow-hidden relative p-3">
              {p.primary_image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={p.primary_image_url}
                  alt={p.name}
                  className={`w-full h-full object-contain group-hover:scale-105 transition-transform duration-300 drop-shadow-sm ${!p.in_stock ? 'grayscale opacity-70' : ''}`}
                />
              ) : (
                <span className="text-5xl">🐾</span>
              )}
              <div className={`absolute top-2 left-2 text-xs font-medium px-2 py-0.5 rounded-full ${
                p.in_stock
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-amber-100 text-amber-700 border border-amber-200'
              }`}>
                {p.in_stock ? 'Disponible' : 'Agotado · Lo conseguimos'}
              </div>
            </div>
            <div className="p-3 space-y-1">
              <h3 className="font-medium text-sm leading-tight line-clamp-2">{p.name}</h3>
              <p className={`font-bold ${p.in_stock ? 'text-brand-700' : 'text-gray-400'}`}>
                {formatCurrency(Number(p.price))}
              </p>
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
