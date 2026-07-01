import { Suspense } from 'react';
import { storeApi } from '@/lib/api';
import Link from 'next/link';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { BreadcrumbSchema } from '@/components/seo/JsonLd';
import { CatalogGrid, type FilterChip } from '@/components/CatalogGrid';
import { FilterSidebar } from '@/components/catalog/FilterSidebar';

export const revalidate = 1800; // 30 min

const SLUG_STRATEGY: Record<string, {
  type: 'species' | 'category' | 'all';
  value?: string;
  label: string;
  emoji: string;
  description: string;
  pet_type?: string;
}> = {
  perros:     { type: 'species',  value: 'perro',      label: 'Perros',            emoji: '🐕', description: 'Alimento, accesorios y cuidado para perros',             pet_type: 'dog'  },
  gatos:      { type: 'species',  value: 'gato',       label: 'Gatos',             emoji: '🐈', description: 'Alimento, accesorios y cuidado para gatos',              pet_type: 'cat'  },
  accesorios: { type: 'category', value: 'accesorios', label: 'Accesorios',        emoji: '🎀', description: 'Correas, collares, juguetes y más'  },
  snacks:     { type: 'category', value: 'snack',      label: 'Snacks y premios',  emoji: '🦴', description: 'Premios y golosinas saludables para tus mascotas' },
  todos:      { type: 'all',                           label: 'Todo el catálogo',  emoji: '🐾', description: 'Todos nuestros productos para mascotas' },
};

const FILTER_CHIPS: Record<string, FilterChip[]> = {
  perros:     [
    { label: 'Concentrado', keyword: 'concentrado', categorySlug: 'concentrado' },
    { label: 'Snacks',      keyword: 'snack',        categorySlug: 'snacks'      },
    { label: 'Higiene',     keyword: 'higiene',      categorySlug: 'higiene'     },
    { label: 'Salud',       keyword: 'salud',        categorySlug: 'medicamentos'},
    { label: 'Accesorios',  keyword: 'accesorio',    categorySlug: 'accesorios'  },
  ],
  gatos:      [
    { label: 'Concentrado', keyword: 'concentrado', categorySlug: 'concentrado' },
    { label: 'Snacks',      keyword: 'snack',        categorySlug: 'snacks'      },
    { label: 'Higiene',     keyword: 'higiene',      categorySlug: 'higiene'     },
    { label: 'Salud',       keyword: 'salud',        categorySlug: 'medicamentos'},
  ],
  snacks:     [{ label: 'Dental', keyword: 'dental' }, { label: 'Natural', keyword: 'natural' }, { label: 'Perro', keyword: 'perro' }, { label: 'Gato', keyword: 'gato' }],
  todos:      [
    { label: 'Concentrado',  keyword: 'concentrado', categorySlug: 'concentrado'  },
    { label: 'Snacks',       keyword: 'snack',        categorySlug: 'snacks'       },
    { label: 'Higiene',      keyword: 'higiene',      categorySlug: 'higiene'      },
    { label: 'Medicamentos', keyword: 'medicamento',  categorySlug: 'medicamentos' },
    { label: 'Accesorios',   keyword: 'accesorio',    categorySlug: 'accesorios'   },
  ],
};

interface Props {
  params: { slug: string };
  searchParams: Record<string, string | string[] | undefined>;
}

export async function generateMetadata({ params, searchParams }: Props) {
  const slug = decodeURIComponent(params.slug);
  const s = SLUG_STRATEGY[slug];
  const label = s?.label ?? slug.charAt(0).toUpperCase() + slug.slice(1);

  const lifeStage = searchParams.life_stage;
  const sizeRange = searchParams.size_range;
  const titleSuffix = [
    lifeStage ? `${lifeStage}` : '',
    sizeRange ? `talla ${sizeRange}` : '',
  ].filter(Boolean).join(' ');

  return {
    title: titleSuffix
      ? `${label} ${titleSuffix} — Bigotes y Paticas`
      : `${label} — Bigotes y Paticas`,
    description: s?.description ?? `Productos ${label} para mascotas`,
    alternates: { canonical: `https://bigotesypaticas.com/categorias/${slug}` },
  };
}

export default async function CategoryPage({ params, searchParams }: Props) {
  const slug = decodeURIComponent(params.slug);
  const strategy = SLUG_STRATEGY[slug];

  // Advanced filter params from URL
  const lifeStage = Array.isArray(searchParams.life_stage)
    ? searchParams.life_stage.join(',')
    : searchParams.life_stage;
  const sizeRange = Array.isArray(searchParams.size_range)
    ? searchParams.size_range.join(',')
    : searchParams.size_range;
  const brand = Array.isArray(searchParams.brand)
    ? searchParams.brand.join(',')
    : searchParams.brand;
  const petType = Array.isArray(searchParams.pet_type)
    ? searchParams.pet_type.join(',')
    : searchParams.pet_type;

  const subCat = Array.isArray(searchParams.sub_cat)
    ? searchParams.sub_cat[0]
    : searchParams.sub_cat;

  const hasAdvancedFilters = !!(lifeStage || sizeRange || brand || petType);
  const hasAnyFilters = hasAdvancedFilters || !!subCat;

  // Resolve category slug for the catalog endpoint
  let categorySlugForApi: string | undefined;
  if (subCat) {
    // sub_cat (chip de subcategoría) toma prioridad
    categorySlugForApi = subCat;
  } else if (strategy?.type === 'category' && strategy.value) {
    categorySlugForApi = strategy.value;
  } else if (!strategy) {
    categorySlugForApi = slug;
  }
  // For species (perros/gatos), always include pet_type
  const effectivePetType = petType ?? strategy?.pet_type;

  // Fetch data: prefer catalogFiltered for advanced filters or when facets needed
  const [catalogData, legacyData, categories] = await Promise.all([
    storeApi.catalogFiltered({
      category_slug: categorySlugForApi,
      life_stage: lifeStage,
      size_range: sizeRange,
      brand: brand,
      pet_type: effectivePetType,
      page_size: 40,
    }),
    // Legacy list solo para páginas de especie sin ningún filtro activo
    strategy?.type === 'species' && !hasAnyFilters
      ? storeApi.list({ species: strategy.value, per_page: 40 })
      : Promise.resolve(null),
    (strategy?.type === 'category' || !strategy) ? storeApi.categories() : Promise.resolve([]),
  ]);

  // Use legacy data only for simple species pages without any active filter
  const data = (strategy?.type === 'species' && !hasAnyFilters && legacyData)
    ? legacyData
    : { items: catalogData.items, total: catalogData.total };

  const facets = catalogData.facets ?? {};

  const label = strategy?.label ?? (slug.charAt(0).toUpperCase() + slug.slice(1));
  const emoji = strategy?.emoji ?? '🐾';
  const description = strategy?.description;

  const dbCategory = (categories as any[]).find(
    (c: any) => c.slug === (strategy?.value ?? slug)
  );

  // Build load-more query for legacy grid pagination
  const loadMoreParams = new URLSearchParams({ is_published: 'true' });
  if (categorySlugForApi) {
    loadMoreParams.set('category_slug', categorySlugForApi);
  } else if (strategy?.type === 'species' && strategy.value) {
    loadMoreParams.set('species', strategy.value);
  }
  if (effectivePetType && categorySlugForApi) {
    // Cuando hay sub_cat, necesitamos filtrar por pet_type también en load-more
    loadMoreParams.set('pet_type', effectivePetType);
  }

  const filterChips = FILTER_CHIPS[slug] ?? [];
  const hasSidebarFilters = Object.keys(facets).some(
    (k) => Object.keys((facets as any)[k] ?? {}).length > 0
  );

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

      {/* Header */}
      <header className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <span className="text-3xl">{emoji}</span>
          <div>
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
              Catálogo · {label.toUpperCase()}
            </p>
            <h1 className="text-2xl md:text-3xl font-display font-extrabold text-[#0d4a45] leading-tight">
              {(dbCategory as any)?.description ?? description ?? `Productos para ${label.toLowerCase()}`}
            </h1>
          </div>
        </div>
        <p className="text-xs text-muted-foreground mt-1 ml-12">
          <span className="font-semibold text-foreground">{data.total}</span> productos · Envío 24-72h en Pereira y Dosquebradas
        </p>
      </header>

      {/* Layout con sidebar de filtros */}
      <div className="flex gap-8 items-start">
        {/* FilterSidebar — solo si hay facets */}
        {hasSidebarFilters && (
          <Suspense fallback={null}>
            <FilterSidebar facets={facets as any} />
          </Suspense>
        )}

        {/* Grid */}
        <div className="flex-1 min-w-0">
          {data.items.length > 0 ? (
            <CatalogGrid
              key={[lifeStage, sizeRange, brand, petType].filter(Boolean).join('|') || 'default'}
              initialItems={data.items}
              totalCount={data.total}
              apiQuery={loadMoreParams.toString()}
              filterChips={filterChips}
              slug={slug}
            />
          ) : (
            <div className="text-center py-24">
              <div className="text-7xl mb-6">{emoji}</div>
              <h2 className="text-2xl font-display font-bold mb-3">Sin productos con estos filtros</h2>
              <p className="text-muted-foreground mb-8">Prueba con otros filtros o explora el catálogo completo.</p>
              <Link href={`/categorias/${slug}`} className="inline-flex items-center gap-2 btn-primary">
                <ArrowLeft className="h-4 w-4" /> Ver todos los productos
              </Link>
            </div>
          )}
        </div>
      </div>

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
