'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Plus, Package, Pencil, Eye, EyeOff, Star, Filter, Truck, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { products, suppliers, type Product } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select } from '@/components/ui/select';
import { Pagination } from '@/components/ui/pagination';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { formatCurrency } from '@/lib/utils';

// P4: margen real y alerta de venta por debajo del costo
function renderMargin(p: Product) {
  const cost = Number(p.cost) || 0;
  const price = Number(p.price) || 0;
  if (price <= 0) return <span className="text-xs text-muted-foreground">—</span>;
  const marginPct = ((price - cost) / price) * 100;
  if (cost > 0 && price <= cost) {
    return (
      <Badge variant="danger" className="gap-1">
        <AlertTriangle className="w-3 h-3" /> Bajo costo
      </Badge>
    );
  }
  const cls = marginPct < 15 ? 'text-amber-600' : marginPct < 30 ? 'text-foreground' : 'text-emerald-600';
  return <span className={`text-sm font-semibold ${cls}`}>{marginPct.toFixed(0)}%</span>;
}

export default function ProductsPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [filterPublished, setFilterPublished] = useState<string>('all');
  const [filterSupplier, setFilterSupplier] = useState<string>('all');
  const [editProduct, setEditProduct] = useState<Product | null>(null);
  const [openCreate, setOpenCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['products', q, page, filterPublished, filterSupplier],
    queryFn: () => products.list({
      q: q || undefined,
      page,
      page_size: 50,
      is_published: filterPublished === 'all' ? undefined : filterPublished === 'published',
      supplier_id: filterSupplier !== 'all' && filterSupplier !== 'none' ? filterSupplier : undefined,
      without_supplier: filterSupplier === 'none' ? true : undefined,
    }),
  });

  const { data: brands } = useQuery({ queryKey: ['brands'], queryFn: products.brands });
  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: products.categories });
  const { data: suppliersData } = useQuery({
    queryKey: ['suppliers-all'],
    queryFn: () => suppliers.list({ is_active: true, page_size: 200 }),
  });
  const supplierList = suppliersData?.items ?? [];

  const createMut = useMutation({
    mutationFn: (p: Parameters<typeof products.create>[0]) => products.create(p),
    onSuccess: () => { toast.success('Producto creado'); qc.invalidateQueries({ queryKey: ['products'] }); setOpenCreate(false); },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<Product> }) => products.update(id, payload),
    onSuccess: () => { toast.success('Producto actualizado'); qc.invalidateQueries({ queryKey: ['products'] }); setEditProduct(null); },
    onError: (e: Error) => toast.error(e.message),
  });

  const togglePublish = (p: Product) =>
    updateMut.mutate({ id: p.id, payload: { is_published: !p.is_published } });

  const toggleFeatured = (p: Product) =>
    updateMut.mutate({ id: p.id, payload: { is_featured: !p.is_featured } });

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <Package className="w-6 h-6 text-brand-600" /> Productos
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {data?.total ?? 0} productos · {data?.items.filter((p) => p.is_published).length ?? 0} publicados
          </p>
        </div>
        <Button onClick={() => setOpenCreate(true)}>
          <Plus className="h-4 w-4" /> Nuevo producto
        </Button>
      </div>

      {/* Filtros */}
      <div className="flex gap-3 items-center flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Nombre o SKU…"
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1); }}
            className="pl-10"
          />
        </div>
        <Select value={filterPublished} onChange={(e) => { setFilterPublished(e.target.value); setPage(1); }} className="w-40">
          <option value="all">Todos</option>
          <option value="published">Publicados</option>
          <option value="draft">Borradores</option>
        </Select>
        <Select value={filterSupplier} onChange={(e) => { setFilterSupplier(e.target.value); setPage(1); }} className="w-52">
          <option value="all">Todos los proveedores</option>
          <option value="none">⚠️ Sin proveedor</option>
          {supplierList.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </Select>
      </div>

      {isLoading && <div className="text-center py-12 text-muted-foreground">Cargando…</div>}

      {data && data.items.length === 0 && (
        <Card className="p-12 text-center">
          <Package className="h-12 w-12 mx-auto text-muted-foreground mb-4 opacity-30" />
          <p className="text-muted-foreground">Sin productos {q ? `para "${q}"` : ''}</p>
        </Card>
      )}

      {data && data.items.length > 0 && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-muted-foreground text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left p-4">Producto</th>
                  <th className="text-left p-4">SKU</th>
                  <th className="text-left p-4">Proveedor</th>
                  <th className="text-right p-4">Costo</th>
                  <th className="text-right p-4">Precio</th>
                  <th className="text-center p-4">Margen</th>
                  <th className="text-center p-4">Estado</th>
                  <th className="text-center p-4">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((p) => (
                  <tr key={p.id} className="border-t border-border hover:bg-accent/20 transition-colors">
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        {p.primary_image_url ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={p.primary_image_url} alt="" className="h-10 w-10 rounded-lg object-cover border border-border" />
                        ) : (
                          <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center shrink-0">
                            <Package className="h-4 w-4 text-muted-foreground" />
                          </div>
                        )}
                        <div>
                          <div className="font-medium line-clamp-1">{p.name}</div>
                          {p.short_description && (
                            <div className="text-xs text-muted-foreground line-clamp-1">{p.short_description}</div>
                          )}
                          {p.is_featured && <Badge variant="brand" className="mt-0.5">⭐ Destacado</Badge>}
                        </div>
                      </div>
                    </td>
                    <td className="p-4 font-mono text-xs">{p.sku}</td>
                    <td className="p-4">
                      {p.supplier_name ? (
                        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                          <Truck className="w-3 h-3" /> {p.supplier_name}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs text-amber-600">
                          <AlertTriangle className="w-3 h-3" /> Sin proveedor
                        </span>
                      )}
                    </td>
                    <td className="p-4 text-right text-muted-foreground">{formatCurrency(p.cost)}</td>
                    <td className="p-4 text-right font-semibold">{formatCurrency(p.price)}</td>
                    <td className="p-4 text-center">{renderMargin(p)}</td>
                    <td className="p-4 text-center">
                      <Badge variant={p.is_published ? 'success' : 'neutral'}>
                        {p.is_published ? 'Publicado' : 'Borrador'}
                      </Badge>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          title="Editar"
                          onClick={() => setEditProduct(p)}
                          className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button
                          title={p.is_published ? 'Despublicar' : 'Publicar'}
                          onClick={() => togglePublish(p)}
                          className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
                        >
                          {p.is_published ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                        </button>
                        <button
                          title={p.is_featured ? 'Quitar destacado' : 'Destacar'}
                          onClick={() => toggleFeatured(p)}
                          className={`p-1.5 rounded hover:bg-muted ${p.is_featured ? 'text-amber-500' : 'text-muted-foreground hover:text-foreground'}`}
                        >
                          <Star className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4">
            {data && <Pagination page={page} pageSize={50} total={data.total} onPageChange={setPage} />}
          </div>
        </Card>
      )}

      {/* Modal crear */}
      <Dialog open={openCreate} onClose={() => setOpenCreate(false)} title="Nuevo producto" size="lg">
        <ProductForm
          brands={brands || []}
          categories={categories || []}
          suppliers={supplierList}
          onSubmit={(p) => createMut.mutate(p as any)}
          loading={createMut.isPending}
        />
      </Dialog>

      {/* Modal editar */}
      <Dialog open={!!editProduct} onClose={() => setEditProduct(null)} title="Editar producto" size="lg">
        {editProduct && (
          <ProductForm
            initial={editProduct}
            brands={brands || []}
            categories={categories || []}
            suppliers={supplierList}
            onSubmit={(p) => updateMut.mutate({ id: editProduct.id, payload: p })}
            loading={updateMut.isPending}
          />
        )}
      </Dialog>
    </div>
  );
}

type ProductFormProps = {
  initial?: Product;
  brands: { id: string; name: string }[];
  categories: { id: string; name: string }[];
  suppliers: { id: string; name: string }[];
  onSubmit: (p: Partial<Product> & { sku?: string; name?: string }) => void;
  loading: boolean;
};

function ProductForm({ initial, brands, categories, suppliers, onSubmit, loading }: ProductFormProps) {
  const initialAttrs = (initial?.attributes ?? {}) as Record<string, unknown>;
  const [form, setForm] = useState({
    sku: initial?.sku || '',
    name: initial?.name || '',
    short_description: initial?.short_description || '',
    description: initial?.description || '',
    cost: initial?.cost ? String(initial.cost) : '',
    price: initial?.price ? String(initial.price) : '',
    compare_at_price: initial?.compare_at_price ? String(initial.compare_at_price) : '',
    brand_id: initial?.brand_id || '',
    category_id: initial?.category_id || '',
    primary_image_url: initial?.primary_image_url || '',
    is_active: initial?.is_active ?? true,
    is_published: initial?.is_published ?? false,
    is_featured: initial?.is_featured ?? false,
    tags: initial?.tags?.join(', ') || '',
    tax_pct: initialAttrs.tax_pct != null ? String(initialAttrs.tax_pct) : '19',
    // Filtros de catálogo — columnas directas (no attributes)
    pet_type: initial?.pet_type || '',
    life_stage: initial?.life_stage || '',
    size_range: initial?.size_range || '',
    supplier_id: initial?.supplier_id || '',
  });

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: any = {
      sku: form.sku,
      name: form.name,
      short_description: form.short_description || null,
      description: form.description || null,
      cost: form.cost ? parseFloat(form.cost) : 0,
      price: form.price ? parseFloat(form.price) : 0,
      compare_at_price: form.compare_at_price ? parseFloat(form.compare_at_price) : null,
      brand_id: form.brand_id || null,
      category_id: form.category_id || null,
      primary_image_url: form.primary_image_url || null,
      is_active: form.is_active,
      is_published: form.is_published,
      is_featured: form.is_featured,
      tags: form.tags ? form.tags.split(',').map((t) => t.trim()).filter(Boolean) : [],
      // IVA en attributes (JSONB)
      attributes: {
        ...initialAttrs,
        tax_pct: form.tax_pct !== '' ? Number(form.tax_pct) : 0,
      },
      // Filtros de catálogo — columnas directas
      pet_type: form.pet_type || null,
      life_stage: form.life_stage || null,
      size_range: form.size_range || null,
    };
    // Proveedor: solo enviar si cambia o se asigna (vincula via supplier_sku_map)
    if (form.supplier_id) {
      payload.supplier_id = form.supplier_id;
    }
    onSubmit(payload);
  }

  return (
    <form onSubmit={handleSubmit}>
      <DialogBody className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium mb-1 block">SKU *</label>
            <Input value={form.sku} onChange={(e) => set('sku', e.target.value)} required placeholder="Ej: BYP-001" />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Nombre *</label>
            <Input value={form.name} onChange={(e) => set('name', e.target.value)} required placeholder="Nombre del producto" />
          </div>
        </div>
        <div>
          <label className="text-xs font-medium mb-1 block">Descripción corta</label>
          <Input value={form.short_description} onChange={(e) => set('short_description', e.target.value)} placeholder="Breve descripción visible en listados" />
        </div>
        <div>
          <label className="text-xs font-medium mb-1 block">Descripción completa</label>
          <textarea
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
            rows={3}
            placeholder="Descripción detallada…"
            className="w-full px-3 py-2 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-xs font-medium mb-1 block">Costo</label>
            <Input type="number" min="0" step="0.01" value={form.cost} onChange={(e) => set('cost', e.target.value)} placeholder="0" />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Precio venta *</label>
            <Input type="number" min="0" step="0.01" value={form.price} onChange={(e) => set('price', e.target.value)} placeholder="0" required />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Precio antes</label>
            <Input type="number" min="0" step="0.01" value={form.compare_at_price} onChange={(e) => set('compare_at_price', e.target.value)} placeholder="Tachado" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium mb-1 block">Marca</label>
            <Select value={form.brand_id} onChange={(e) => set('brand_id', e.target.value)}>
              <option value="">Sin marca</option>
              {brands.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </Select>
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Categoría</label>
            <Select value={form.category_id} onChange={(e) => set('category_id', e.target.value)}>
              <option value="">Sin categoría</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
          </div>
        </div>
        <div>
          <label className="text-xs font-medium mb-1 block">Proveedor</label>
          <Select value={form.supplier_id} onChange={(e) => set('supplier_id', e.target.value)}>
            <option value="">Sin proveedor</option>
            {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </Select>
          <p className="text-[11px] text-muted-foreground mt-1">Proveedor principal de este producto (para compras y reabastecimiento).</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium mb-1 block">IVA del producto</label>
            <Select value={form.tax_pct} onChange={(e) => set('tax_pct', e.target.value)}>
              <option value="0">0% (Excluido / Exento)</option>
              <option value="5">5%</option>
              <option value="19">19% (General)</option>
            </Select>
            <p className="text-[11px] text-muted-foreground mt-1">Tarifa de IVA aplicable a este producto.</p>
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">¿Para qué mascota?</label>
            <Select value={form.pet_type} onChange={(e) => set('pet_type', e.target.value)}>
              <option value="">Sin especificar</option>
              <option value="dog">🐶 Perro</option>
              <option value="cat">🐱 Gato</option>
              <option value="both">🐾 Perro y Gato</option>
              <option value="small_pet">🐹 Mascota pequeña</option>
            </Select>
            <p className="text-[11px] text-muted-foreground mt-1">Define la especie objetivo del producto.</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium mb-1 block">Etapa de vida</label>
            <Select value={form.life_stage} onChange={(e) => set('life_stage', e.target.value)}>
              <option value="">Sin especificar</option>
              <option value="puppy">🐣 Cachorro</option>
              <option value="adult">🐕 Adulto</option>
              <option value="senior">🦮 Senior</option>
              <option value="all">🐾 Todas las edades</option>
            </Select>
            <p className="text-[11px] text-muted-foreground mt-1">Filtra por etapa de vida en la tienda.</p>
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Tamaño de raza</label>
            <Select value={form.size_range} onChange={(e) => set('size_range', e.target.value)}>
              <option value="">Sin especificar</option>
              <option value="mini">Mini (0–4 kg)</option>
              <option value="small">Pequeño (5–10 kg)</option>
              <option value="medium">Mediano (11–25 kg)</option>
              <option value="large">Grande (26–45 kg)</option>
              <option value="giant">Gigante (+45 kg)</option>
              <option value="all">Todos los tamaños</option>
            </Select>
            <p className="text-[11px] text-muted-foreground mt-1">Filtra por tamaño de raza en la tienda.</p>
          </div>
        </div>
        <div>
          <label className="text-xs font-medium mb-1 block">URL imagen principal</label>
          <Input value={form.primary_image_url} onChange={(e) => set('primary_image_url', e.target.value)} placeholder="https://…" />
        </div>
        <div>
          <label className="text-xs font-medium mb-1 block">Tags (separados por coma)</label>
          <Input value={form.tags} onChange={(e) => set('tags', e.target.value)} placeholder="perro, alimento, premium" />
        </div>
        <div className="flex gap-4 flex-wrap">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.is_active} onChange={(e) => set('is_active', e.target.checked)} className="rounded" />
            <span className="text-sm">Activo</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.is_published} onChange={(e) => set('is_published', e.target.checked)} className="rounded" />
            <span className="text-sm">Publicado (visible en tienda)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.is_featured} onChange={(e) => set('is_featured', e.target.checked)} className="rounded" />
            <span className="text-sm">⭐ Destacado</span>
          </label>
        </div>
      </DialogBody>
      <DialogFooter>
        <Button type="submit" disabled={loading || !form.name || !form.sku}>
          {loading ? 'Guardando…' : initial ? 'Guardar cambios' : 'Crear producto'}
        </Button>
      </DialogFooter>
    </form>
  );
}
