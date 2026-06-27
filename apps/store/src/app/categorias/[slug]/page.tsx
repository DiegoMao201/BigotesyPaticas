import { storeApi } from '@/lib/api';
import Link from 'next/link';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { BreadcrumbSchema } from '@/components/seo/JsonLd';
import { CatalogGrid, type FilterChip } from '@/components/CatalogGrid';

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

// Chips de filtro por slug (búsqueda client-side en nombre de producto)
const FILTER_CHIPS: Record<string, FilterChip[]> = {
  perros: [
    { label: 'Concentrado', keyword: 'concentrado' },
    { label: 'Snacks', keyword: 'snack' },
    { label: 'Higiene', keyword: 'higiene' },
    { label: 'Salud', keyword: 'salud' },
    { label: 'Accesorios', keyword: 'accesorio' },
  ],
  gatos: [
    { label: 'Concentrado', keyword: 'concentrado' },
    { label: 'Snacks', keyword: 'snack' },
    { label: 'Higiene', keyword: 'higiene' },
    { label: 'Salud', keyword: 'salud' },
  ],
  snacks: [
    { label: 'Dental', keyword: 'dental' },
    { label: 'Natural', keyword: 'natural' },
    { label: 'Perro', keyword: 'perro' },
    { label: 'Gato', keyword: 'gato' },
  ],
  todos: [
    { label: 'Concentrado', keyword: 'concentrado' },
    { label: 'Snacks', keyword: 'snack' },
    { label: 'Higiene', keyword: 'higiene' },
    { label: 'Medicamento', keyword: 'medicamento' },
    { label: 'Accesorio', keyword: 'accesorio' },
  ],
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

  const listParams: Parameters<typeof storeApi.list>[0] = { per_page: 40 };

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

  // Query string para paginación client-side
  const loadMoreParams = new URLSearchParams({ is_published: 'true' });
  if (strategy?.type === 'species' && strategy.value) {
    loadMoreParams.set('species', strategy.value);
  } else if (strategy?.type === 'category' && strategy.value) {
    loadMoreParams.set('category_slug', strategy.value);
  } else if (!strategy) {
    loadMoreParams.set('category_slug', slug);
  }

  const filterChips = FILTER_CHIPS[slug] ?? [];

  return (
    <div className="container-wide py-8">
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: label, url: `https://bigotesypaticas.com/categorias/${slug}` },
        ]}
      />
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground mb-6">
        <Link href="/" className="hover:text-brand-600 transition-colors flex items-center gap-1">
          <ArrowLeft className="h-3 w-3" /> Inicio
        </Link>
        <span>/</span>
        <span className="text-foreground font-medium">{label}</span>
      </div>

      {/* Header compacto */}
      <header className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <span className="text-3xl">{emoji}</span>
          <div>
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
              Catálogo · {label.toUpperCase()}
            </p>
            <h1 className="text-2xl md:text-3xl font-display font-extrabold text-[#0d4a45] leading-tight">
              {dbCategory?.description ?? description ?? `Productos para ${label.toLowerCase()}`}
            </h1>
          </div>
        </div>
        <p className="text-xs text-muted-foreground mt-1 ml-12">
          <span className="font-semibold text-foreground">{data.total}</span> productos · Envío 24-72h en Pereira y Dosquebradas
        </p>
      </header>

      {/* Grid interactivo con filtros y carga más */}
      {data.items.length > 0 ? (
        <CatalogGrid
          initialItems={data.items}
          totalCount={data.total}
          apiQuery={loadMoreParams.toString()}
          filterChips={filterChips}
          slug={slug}
        />
      ) : (
        <div className="text-center py-24">
          <div className="text-7xl mb-6">{emoji}</div>
          <h2 className="text-2xl font-display font-bold mb-3">Sin productos en esta categoría</h2>
          <p className="text-muted-foreground mb-8">
            Pronto agregaremos más productos. ¡Vuelve pronto!
          </p>
          <Link href="/" className="inline-flex items-center gap-2 btn-primary">
            <ArrowLeft className="h-4 w-4" /> Volver al inicio
          </Link>
        </div>
      )}

      {/* Otras categorías */}
      {data.items.length > 0 && (
        <div className="mt-16 pt-8 border-t border-border">
          <h3 className="text-xs font-semibold text-muted-foreground mb-4 uppercase tracking-wider">
            Explorar otras categorías
          </h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(SLUG_STRATEGY)
              .filter(([s]) => s !== slug && s !== 'todos')
              .map(([s, info]) => (
                <Link
                  key={s}
                  href={`/categorias/${s}`}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-full border border-border
                             bg-card hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700
                             transition-all text-sm font-medium"
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
