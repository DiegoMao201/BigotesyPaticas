'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Truck, Search, Plus, Pencil, Trash2, Package, Phone, Mail, MapPin } from 'lucide-react';
import { toast } from 'sonner';
import { suppliers, type Supplier, type SupplierIn, type SupplierSkuInsight } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { Pagination } from '@/components/ui/pagination';

export default function SuppliersPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(true);
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Supplier | null>(null);
  const [creating, setCreating] = useState(false);
  const [skusOf, setSkusOf] = useState<Supplier | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['suppliers', search, activeFilter, page],
    queryFn: () => suppliers.list({ q: search || undefined, is_active: activeFilter, page, page_size: 20 }),
  });

  const delMut = useMutation({
    mutationFn: (id: string) => suppliers.delete(id),
    onSuccess: () => {
      toast.success('Proveedor desactivado');
      qc.invalidateQueries({ queryKey: ['suppliers'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Truck className="h-8 w-8 text-orange-500" />
            Proveedores
          </h1>
          <p className="text-gray-600 mt-1">Gestión de proveedores y sus SKUs</p>
        </div>
        <Button onClick={() => setCreating(true)} className="bg-orange-500 hover:bg-orange-600">
          <Plus className="h-4 w-4 mr-2" />Nuevo proveedor
        </Button>
      </div>

      <Card className="p-4 flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[260px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Buscar por nombre, NIT, email..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-10"
          />
        </div>
        <div className="flex gap-2">
          <Button
            variant={activeFilter === true ? 'default' : 'outline'}
            onClick={() => { setActiveFilter(true); setPage(1); }}
            className={activeFilter === true ? 'bg-orange-500 hover:bg-orange-600' : ''}
          >Activos</Button>
          <Button
            variant={activeFilter === false ? 'default' : 'outline'}
            onClick={() => { setActiveFilter(false); setPage(1); }}
          >Inactivos</Button>
          <Button
            variant={activeFilter === undefined ? 'default' : 'outline'}
            onClick={() => { setActiveFilter(undefined); setPage(1); }}
          >Todos</Button>
        </div>
      </Card>

      {isLoading ? (
        <Card className="p-12 text-center text-gray-500">Cargando proveedores...</Card>
      ) : !data?.items.length ? (
        <Card className="p-12 text-center text-gray-500">
          <Truck className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          No hay proveedores. Crea el primero.
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.items.map((s) => (
              <Card
                key={s.id}
                className="p-4 hover:shadow-lg transition cursor-pointer"
                onClick={() => setSkusOf(s)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="min-w-0 flex-1">
                    <h3 className="font-bold text-lg truncate">{s.name}</h3>
                    <p className="text-xs text-gray-500">NIT {s.nit}</p>
                  </div>
                  <div className="flex gap-1">
                    {!s.is_active && <Badge variant="neutral">Inactivo</Badge>}
                    <Badge className="bg-orange-100 text-orange-700">
                      <Package className="h-3 w-3 mr-1" />{s.sku_count} SKUs
                    </Badge>
                  </div>
                </div>
                <div className="space-y-1 text-sm text-gray-600 mt-3">
                  {s.phone && <div className="flex items-center gap-2"><Phone className="h-3 w-3" />{s.phone}</div>}
                  {s.email && <div className="flex items-center gap-2 truncate"><Mail className="h-3 w-3" />{s.email}</div>}
                  {s.address && <div className="flex items-center gap-2 truncate"><MapPin className="h-3 w-3" />{s.address}</div>}
                  {s.contact_name && <div className="text-xs">Contacto: <span className="font-medium">{s.contact_name}</span></div>}
                  <div className="text-xs">Pago a {s.payment_terms_days} días</div>
                </div>
                <div className="flex gap-2 mt-4 pt-3 border-t">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => { e.stopPropagation(); setSkusOf(s); }}
                    className="flex-1"
                  >
                    <Package className="h-3 w-3 mr-1" />SKUs
                  </Button>
                  <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); setEditing(s); }}>
                    <Pencil className="h-3 w-3" />
                  </Button>
                  {s.is_active && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`¿Desactivar ${s.name}?`)) delMut.mutate(s.id);
                      }}
                      className="text-red-600 hover:bg-red-50"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </Card>
            ))}
          </div>

          <Pagination page={page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
        </>
      )}

      {(creating || editing) && (
        <SupplierFormDialog
          supplier={editing}
          onClose={() => { setCreating(false); setEditing(null); }}
          onSaved={() => qc.invalidateQueries({ queryKey: ['suppliers'] })}
        />
      )}

      {skusOf && <SupplierSkusDialog supplier={skusOf} onClose={() => setSkusOf(null)} />}
    </div>
  );
}

function SupplierFormDialog({ supplier, onClose, onSaved }: { supplier: Supplier | null; onClose: () => void; onSaved: () => void }) {
  const isEdit = !!supplier;
  const [form, setForm] = useState<SupplierIn>({
    nit: supplier?.nit || '',
    name: supplier?.name || '',
    email: supplier?.email || '',
    phone: supplier?.phone || '',
    address: supplier?.address || '',
    contact_name: supplier?.contact_name || '',
    payment_terms_days: supplier?.payment_terms_days || 30,
    notes: supplier?.notes || '',
  });

  const mut = useMutation({
    mutationFn: () => isEdit ? suppliers.update(supplier!.id, form) : suppliers.create(form),
    onSuccess: () => {
      toast.success(isEdit ? 'Proveedor actualizado' : 'Proveedor creado');
      onSaved();
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Dialog open onClose={onClose} title={isEdit ? `Editar ${supplier!.name}` : 'Nuevo proveedor'} size="lg">
      <DialogBody>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm font-medium">NIT *</label>
            <Input value={form.nit} onChange={(e) => setForm({ ...form, nit: e.target.value })} required />
          </div>
          <div>
            <label className="text-sm font-medium">Nombre *</label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div>
            <label className="text-sm font-medium">Teléfono (con código país)</label>
            <Input value={form.phone || ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="573001234567" />
          </div>
          <div>
            <label className="text-sm font-medium">Email</label>
            <Input type="email" value={form.email || ''} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div className="col-span-2">
            <label className="text-sm font-medium">Dirección</label>
            <Input value={form.address || ''} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium">Contacto</label>
            <Input value={form.contact_name || ''} onChange={(e) => setForm({ ...form, contact_name: e.target.value })} />
          </div>
          <div>
            <label className="text-sm font-medium">Días de pago</label>
            <Input type="number" value={form.payment_terms_days} onChange={(e) => setForm({ ...form, payment_terms_days: Number(e.target.value) })} />
          </div>
          <div className="col-span-2">
            <label className="text-sm font-medium">Notas</label>
            <Input value={form.notes || ''} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
        </div>
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cancelar</Button>
        <Button onClick={() => mut.mutate()} disabled={mut.isPending || !form.nit || !form.name} className="bg-orange-500 hover:bg-orange-600">
          {mut.isPending ? 'Guardando...' : 'Guardar'}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}

function SupplierSkusDialog({ supplier, onClose }: { supplier: Supplier; onClose: () => void }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['supplier-skus', supplier.id],
    queryFn: () => suppliers.listSkus(supplier.id, { velocity_days: 30 }),
  });

  const items = data?.items ?? [];
  const summary = data?.summary;
  const urgent = items.filter((x) => x.urgency === 'AGOTADO' || x.urgency === 'URGENTE_8D');

  const urgencyBadge = (i: SupplierSkuInsight) => {
    if (i.urgency === 'AGOTADO') return <Badge className="bg-red-100 text-red-700">Agotado</Badge>;
    if (i.urgency === 'URGENTE_8D') return <Badge className="bg-orange-100 text-orange-700">Urgente 8d</Badge>;
    if (i.urgency === 'REPOSICION_15D') return <Badge className="bg-amber-100 text-amber-700">Reponer 15d</Badge>;
    if (i.urgency === 'MONITOREAR_20D') return <Badge className="bg-blue-100 text-blue-700">Monitorear 20d</Badge>;
    return <Badge variant="neutral">OK</Badge>;
  };

  return (
    <Dialog open onClose={onClose} title={`Productos de ${supplier.name}`} size="lg">
      <DialogBody>
        {isLoading ? (
          <div className="text-center py-8 text-gray-500">Cargando...</div>
        ) : isError ? (
          <div className="text-center py-8 text-red-600">
            Error cargando productos del proveedor: {(error as Error)?.message || 'error desconocido'}
          </div>
        ) : !items.length ? (
          <div className="text-center py-8 text-gray-500">
            <Package className="h-10 w-10 mx-auto mb-2 text-gray-300" />
            Este proveedor aún no tiene productos asociados.
            <p className="text-xs mt-2">Se asocian automáticamente al registrar compras por XML/manual con SKU proveedor.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {summary && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Card className="p-3">
                  <div className="text-xs text-gray-500">Asociados</div>
                  <div className="text-xl font-bold">{summary.associated_products}</div>
                </Card>
                <Card className="p-3 border-orange-200">
                  <div className="text-xs text-orange-600">Urgentes (8 días)</div>
                  <div className="text-xl font-bold text-orange-700">{summary.urgent_8d}</div>
                </Card>
                <Card className="p-3">
                  <div className="text-xs text-gray-500">Unid sugeridas 8d</div>
                  <div className="text-xl font-bold">{summary.recommended_units_8d}</div>
                </Card>
                <Card className="p-3">
                  <div className="text-xs text-gray-500">Unid sugeridas 15d</div>
                  <div className="text-xl font-bold">{summary.recommended_units_15d}</div>
                </Card>
              </div>
            )}

            <div className="rounded-lg border border-orange-200 bg-orange-50/50 p-3">
              <div className="font-medium text-sm mb-2">Recompra urgente por rotación (8 días)</div>
              {!urgent.length ? (
                <div className="text-sm text-gray-600">No hay productos urgentes en este proveedor.</div>
              ) : (
                <div className="space-y-2">
                  {urgent.map((u) => (
                    <div key={u.id} className="flex items-center justify-between gap-3 rounded-md bg-white border p-2">
                      <div className="min-w-0">
                        <div className="font-medium text-sm truncate">{u.product_name}</div>
                        <div className="text-xs text-gray-500 font-mono">{u.product_sku} · Prov: {u.sku_proveedor}</div>
                      </div>
                      <div className="text-right text-xs shrink-0">
                        <div>Stock: <strong>{u.stock_available}</strong></div>
                        <div>V/día: <strong>{u.avg_daily_sales.toFixed(2)}</strong></div>
                        <div className="text-orange-700">Comprar 8d: <strong>{u.reorder_qty_8d}</strong></div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="overflow-auto max-h-80 rounded-lg border">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="text-left p-2">SKU Proveedor</th>
                    <th className="text-left p-2">Producto</th>
                    <th className="text-right p-2">Stock</th>
                    <th className="text-right p-2">Cobertura</th>
                    <th className="text-right p-2">Compra 8d</th>
                    <th className="text-right p-2">Costo</th>
                    <th className="text-center p-2">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((s) => (
                    <tr key={s.id} className="border-t">
                      <td className="p-2 font-mono text-xs">{s.sku_proveedor}</td>
                      <td className="p-2">
                        {s.product_name} <span className="text-xs text-gray-500">({s.product_sku})</span>
                      </td>
                      <td className="p-2 text-right">{s.stock_available}</td>
                      <td className="p-2 text-right">{s.days_cover == null ? '∞' : `${s.days_cover}d`}</td>
                      <td className="p-2 text-right font-semibold text-orange-700">{s.reorder_qty_8d}</td>
                      <td className="p-2 text-right">{s.last_unit_cost == null ? '—' : `$${s.last_unit_cost.toLocaleString('es-CO')}`}</td>
                      <td className="p-2 text-center">{urgencyBadge(s)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cerrar</Button>
      </DialogFooter>
    </Dialog>
  );
}
