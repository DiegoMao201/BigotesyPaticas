import { storeApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import Link from 'next/link';
import { ArrowLeft, ArrowRight } from 'lucide-react';

export const dynamic = 'force-dynamic';

// Mapeo slug del nav → estrategia de filtro en la API
const SLUG_STRATEGY: Record<string, {
  type: 'species' | 'category' | 'all';
  value?: string;
  label: string;
  emoji: string;
  description: string;
}> = {
  perros:     { type: 'species',  value: 'perro',      label: 'Perros',            emoji: '🐕', description: 'Alimento, accesorios y cuidado para perros' },
  gatos:      { type: 'species',  value: 'gato',       label: 'Gatos',             emoji: '🐈', description: 'Alimento, accesorios y cuidado para gatos' },
  accesorios: { type: 'category', value: 'accesorios', label: 'Accesorios',        emoji: '🎀', description: 'Correas, collares, juguetes y más' },
  snacks:     { type: 'category', value: 'snack',      label: 'Snacks y premios',  emoji: '🦴', description: 'Premios y golosinas saludables para tus mascotas' },
  todos:      { type: 'all',                           label: 'Todo el catálogo',  emoji: '🐾', description: 'Todos nuestros productos para mascotas' },
};

export async function generateMetadata({ params }: { params: { slug: string } }) {
  const slug = decodeURIComponent(params.slug);
  const s = SLUG_STRATEGY[slug];
  const label = s?.label ?? slug.charAt(0).toUpperCase() + slug.slice(1);
  return {
    title: `${label} — Bigotes y Paticas`,
    description: s?.description ?? `Productos ${label} para mascotas`,
  };
}

export default async function CategoryPage({ params }: { params: { slug: string } }) {
  const slug = decodeURIComponent(params.slug);
  const strategy = SLUG_STRATEGY[slug];

  const listParams: Parameters<typeof storeApi.list>[0] = { per_page: 24 };

  if (strategy?.type === 'species' && strategy.value) {
    listParams.species = strategy.value;
  } else if (strategy?.type === 'category' && strategy.value) {
    listParams.category_slug = strategy.value;
  } else if (!strategy) {
    // Slug desconocido — intentar como slug de categoría directamente
    listParams.category_slug = slug;
  }
  // type === 'all' → sin filtro, todos los publicados

  const [data, categories] = await Promise.all([
    storeApi.list(listParams),
    (strategy?.type === 'category' || !strategy) ? storeApi.categories() : Promise.resolve([]),
  ]);

  const label = strategy?.label ?? (slug.charAt(0).toUpperCase() + slug.slice(1));
  const emoji = strategy?.emoji ?? '🐾';
  const description = strategy?.description;

  const dbCategory = categories.find(
    (c) => c.slug === (strategy?.value ?? slug)
  );

  return (
    <div className="container-wide py-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-8">
        <Link href="/" className="hover:text-brand-600 transition-colors flex items-center gap-1">
          <ArrowLeft className="h-3.5 w-3.5" /> Inicio
        </Link>
        <span>/</span>
        <span className="text-foreground font-medium">{label}</span>
      </div>

      {/* Header de categoría */}
      <div className="flex flex-col md:flex-row md:items-end gap-6 mb-10 pb-8 border-b border-border">
        <div className="flex-1">
          <div className="flex items-center gap-4 mb-2">
            <span className="text-5xl">{emoji}</span>
            <h1 className="text-4xl md:text-5xl font-display font-extrabold">{label}</h1>
          </div>
          {(dbCategory?.description || description) && (
            <p className="text-muted-foreground text-lg mt-2">
              {dbCategory?.description ?? description}
            </p>
          )}
          <p className="text-sm text-muted-foreground mt-3">
            <span className="font-bold text-foreground text-base">{data.total}</span> productos encontrados
          </p>
        </div>

        {dbCategory?.image_url && (
          <div className="hidden md:block w-36 h-36 rounded-3xl overflow-hidden border border-border shadow-sm flex-shrink-0">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={dbCategory.image_url} alt={label} className="w-full h-full object-cover" />
          </div>
        )}
      </div>

      {/* Grid de productos */}
      {data.items.length > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
          {data.items.map((p) => {
            const discount =
              p.compare_at_price && Number(p.compare_at_price) > Number(p.price)
                ? Math.round((1 - Number(p.price) / Number(p.compare_at_price)) * 100)
                : null;
            return (
              <Link
                key={p.id}
                href={`/producto/${p.slug}`}
                className="group rounded-3xl overflow-hidden border border-border bg-card transition-all hover:shadow-warm hover:-translate-y-1 duration-300"
              >
                <div className="aspect-square bg-white flex items-center justify-center relative p-3">
                  {p.primary_image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={p.primary_image_url}
                      alt={p.name}
                      className="w-full h-full object-contain drop-shadow-sm group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="text-6xl group-hover:scale-110 transition-transform duration-300">🐾</div>
                  )}
                  <div className={`absolute top-2 left-2 text-xs font-semibold px-2.5 py-0.5 rounded-full backdrop-blur-sm border ${
                    p.in_stock
                      ? 'bg-emerald-100/90 text-emerald-700 border-emerald-200/60'
                      : 'bg-gray-100/90 text-gray-500 border-gray-200/60'
                  }`}>
                    {p.in_stock ? '✓ Disponible' : 'Agotado'}
                  </div>
                  {discount && (
                    <div className="absolute top-2 right-2 text-xs font-bold px-2 py-0.5 rounded-full bg-brand-600 text-white shadow-sm">
                      -{discount}%
                    </div>
                  )}
                </div>
                <div className="p-4">
                  <h3 className="font-semibold text-sm line-clamp-2 group-hover:text-brand-600 transition-colors leading-snug">
                    {p.name}
                  </h3>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="font-extrabold text-brand-600">{formatCurrency(p.price)}</span>
                    {discount && p.compare_at_price && (
                      <span className="text-xs text-muted-foreground line-through">
                        {formatCurrency(p.compare_at_price)}
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-24">
          <div className="text-7xl mb-6">{emoji}</div>
          <h2 className="text-2xl font-display font-bold mb-3">Sin productos en esta categoría</h2>
          <p className="text-muted-foreground mb-8">
            Pronto agregaremos más productos. ¡Vuelve pronto!
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 btn-primary"
          >
            <ArrowLeft className="h-4 w-4" /> Volver al inicio
          </Link>
        </div>
      )}

      {/* Otras categorías */}
      {data.items.length > 0 && (
        <div className="mt-16 pt-8 border-t border-border">
          <h3 className="text-sm font-semibold text-muted-foreground mb-4 uppercase tracking-wider">Explorar otras categorías</h3>
          <div className="flex flex-wrap gap-3">
            {Object.entries(SLUG_STRATEGY)
              .filter(([s]) => s !== slug && s !== 'todos')
              .map(([s, info]) => (
                <Link
                  key={s}
                  href={`/categorias/${s}`}
                  className="flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-card hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 transition-all text-sm font-medium"
                >
                  <span>{info.emoji}</span> {info.label}
                  <ArrowRight className="h-3 w-3 opacity-50" />
                </Link>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
