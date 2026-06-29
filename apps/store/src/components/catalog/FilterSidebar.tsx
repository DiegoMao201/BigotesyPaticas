'use client';

import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { useCallback, useState } from 'react';
import { ChevronDown, ChevronUp, SlidersHorizontal, X } from 'lucide-react';

export interface Facets {
  life_stages?: Record<string, number>;
  size_ranges?: Record<string, number>;
  brands?: Record<string, number>;
  pet_types?: Record<string, number>;
}

interface FilterSidebarProps {
  facets: Facets;
}

const LIFE_STAGE_LABELS: Record<string, string> = {
  puppy: 'Cachorro',
  adult: 'Adulto',
  senior: 'Senior',
};

const SIZE_RANGE_LABELS: Record<string, string> = {
  mini: 'Mini',
  small: 'Pequeño',
  medium: 'Mediano',
  large: 'Grande',
  giant: 'Gigante',
};

const PET_TYPE_LABELS: Record<string, string> = {
  dog: 'Perro',
  cat: 'Gato',
  small_pet: 'Mascota pequeña',
  fish: 'Pez',
  bird: 'Ave',
};

const BRAND_LABELS: Record<string, string> = {
  hills: "Hill's",
  royal_canin: 'Royal Canin',
  pro_plan: 'Pro Plan',
  solla: 'Solla',
  agility: 'Agility',
  acana: 'Acana',
  taste_of_the_wild: 'Taste of the Wild',
  pedigree: 'Pedigree',
  whiskas: 'Whiskas',
};

function Section({
  title,
  children,
  defaultOpen = true,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-gray-100 pb-4 mb-4">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center justify-between w-full text-sm font-semibold text-gray-800 mb-2"
      >
        {title}
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && <div className="space-y-1.5">{children}</div>}
    </div>
  );
}

function FilterCheckbox({
  label,
  count,
  checked,
  onChange,
}: {
  label: string;
  count?: number;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer group">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-4 h-4 rounded accent-teal-600"
      />
      <span className="text-sm text-gray-700 group-hover:text-teal-700 flex-1">{label}</span>
      {count !== undefined && (
        <span className="text-xs text-gray-400">({count})</span>
      )}
    </label>
  );
}

export function FilterSidebar({ facets }: FilterSidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [mobileOpen, setMobileOpen] = useState(false);

  const getParam = useCallback(
    (key: string) => searchParams.getAll(key),
    [searchParams]
  );

  const updateParam = useCallback(
    (key: string, value: string, checked: boolean) => {
      const params = new URLSearchParams(searchParams.toString());
      const existing = params.getAll(key);
      if (checked) {
        if (!existing.includes(value)) params.append(key, value);
      } else {
        params.delete(key);
        existing.filter((v) => v !== value).forEach((v) => params.append(key, v));
      }
      router.push(`${pathname}?${params.toString()}`, { scroll: false });
      router.refresh();
    },
    [router, pathname, searchParams]
  );

  const clearAll = useCallback(() => {
    router.push(pathname, { scroll: false });
    router.refresh();
  }, [router, pathname]);

  const activeFilters = [
    ...getParam('life_stage').map((v) => ({ key: 'life_stage', value: v, label: LIFE_STAGE_LABELS[v] ?? v })),
    ...getParam('size_range').map((v) => ({ key: 'size_range', value: v, label: SIZE_RANGE_LABELS[v] ?? v })),
    ...getParam('brand').map((v) => ({ key: 'brand', value: v, label: BRAND_LABELS[v] ?? v })),
    ...getParam('pet_type').map((v) => ({ key: 'pet_type', value: v, label: PET_TYPE_LABELS[v] ?? v })),
  ];

  const filterContent = (
    <div className="space-y-0">
      {/* Active filter chips */}
      {activeFilters.length > 0 && (
        <div className="mb-4">
          <div className="flex flex-wrap gap-1.5 mb-2">
            {activeFilters.map(({ key, value, label }) => (
              <button
                key={`${key}-${value}`}
                onClick={() => updateParam(key, value, false)}
                className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-teal-100 text-teal-800 text-xs font-medium hover:bg-teal-200 transition-colors"
              >
                {label}
                <X className="h-3 w-3" />
              </button>
            ))}
          </div>
          <button
            onClick={clearAll}
            className="text-xs text-gray-500 underline hover:text-teal-600"
          >
            Limpiar todos
          </button>
        </div>
      )}

      {/* Etapa de vida */}
      {facets.life_stages && Object.keys(facets.life_stages).length > 0 && (
        <Section title="Etapa de vida">
          {Object.entries(facets.life_stages).map(([stage, count]) => (
            <FilterCheckbox
              key={stage}
              label={LIFE_STAGE_LABELS[stage] ?? stage}
              count={count}
              checked={getParam('life_stage').includes(stage)}
              onChange={(c) => updateParam('life_stage', stage, c)}
            />
          ))}
        </Section>
      )}

      {/* Tamaño de raza */}
      {facets.size_ranges && Object.keys(facets.size_ranges).length > 0 && (
        <Section title="Tamaño de raza">
          {Object.entries(facets.size_ranges).map(([size, count]) => (
            <FilterCheckbox
              key={size}
              label={SIZE_RANGE_LABELS[size] ?? size}
              count={count}
              checked={getParam('size_range').includes(size)}
              onChange={(c) => updateParam('size_range', size, c)}
            />
          ))}
        </Section>
      )}

      {/* Tipo de mascota */}
      {facets.pet_types && Object.keys(facets.pet_types).length > 0 && (
        <Section title="Tipo de mascota">
          {Object.entries(facets.pet_types).map(([pt, count]) => (
            <FilterCheckbox
              key={pt}
              label={PET_TYPE_LABELS[pt] ?? pt}
              count={count}
              checked={getParam('pet_type').includes(pt)}
              onChange={(c) => updateParam('pet_type', pt, c)}
            />
          ))}
        </Section>
      )}

      {/* Marca */}
      {facets.brands && Object.keys(facets.brands).length > 0 && (
        <Section title="Marca" defaultOpen={false}>
          {Object.entries(facets.brands)
            .filter(([, c]) => c > 0)
            .map(([brand, count]) => (
              <FilterCheckbox
                key={brand}
                label={BRAND_LABELS[brand] ?? brand}
                count={count}
                checked={getParam('brand').includes(brand)}
                onChange={(c) => updateParam('brand', brand, c)}
              />
            ))}
        </Section>
      )}
    </div>
  );

  return (
    <>
      {/* Mobile: sticky button + drawer */}
      <div className="lg:hidden">
        <button
          onClick={() => setMobileOpen(true)}
          className="sticky top-14 z-20 flex items-center gap-2 px-4 py-2 rounded-full border border-gray-200 bg-white shadow-sm text-sm font-semibold text-gray-700 hover:border-teal-400 hover:text-teal-700 transition-colors mb-4"
        >
          <SlidersHorizontal className="h-4 w-4" />
          Filtros {activeFilters.length > 0 && `(${activeFilters.length})`}
        </button>

        {mobileOpen && (
          <div className="fixed inset-0 z-50 flex flex-col justify-end">
            <div
              className="absolute inset-0 bg-black/40"
              onClick={() => setMobileOpen(false)}
            />
            <div className="relative bg-white rounded-t-3xl p-6 max-h-[80vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-lg">Filtros</h3>
                <button onClick={() => setMobileOpen(false)}>
                  <X className="h-5 w-5 text-gray-500" />
                </button>
              </div>
              {filterContent}
              <button
                onClick={() => setMobileOpen(false)}
                className="mt-4 w-full py-3 rounded-2xl bg-teal-600 text-white font-semibold"
              >
                Ver resultados
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Desktop: sticky sidebar */}
      <aside className="hidden lg:block w-[260px] shrink-0">
        <div className="sticky top-20 bg-white rounded-2xl border border-gray-100 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <SlidersHorizontal className="h-4 w-4" />
              Filtros
            </h3>
            {activeFilters.length > 0 && (
              <button
                onClick={clearAll}
                className="text-xs text-gray-500 hover:text-teal-600 underline"
              >
                Limpiar todo
              </button>
            )}
          </div>
          {filterContent}
        </div>
      </aside>
    </>
  );
}
