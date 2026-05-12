'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Truck, Search, Plus, Pencil, Trash2, Package, Phone, Mail, MapPin } from 'lucide-react';
import { toast } from 'sonner';
import { suppliers, type Supplier, type SupplierIn } from '@/lib/api';
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
              <Card key={s.id} className="p-4 hover:shadow-lg transition">
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
                  <Button size="sm" variant="outline" onClick={() => setSkusOf(s)} className="flex-1">
                    <Package className="h-3 w-3 mr-1" />SKUs
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setEditing(s)}>
                    <Pencil className="h-3 w-3" />
                  </Button>
                  {s.is_active && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
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
  const { data, isLoading } = useQuery({
    queryKey: ['supplier-skus', supplier.id],
    queryFn: () => suppliers.listSkus(supplier.id),
  });

  return (
    <Dialog open onClose={onClose} title={`SKUs de ${supplier.name}`} size="lg">
      <DialogBody>
        {isLoading ? (
          <div className="text-center py-8 text-gray-500">Cargando...</div>
        ) : !data?.items.length ? (
          <div className="text-center py-8 text-gray-500">
            <Package className="h-10 w-10 mx-auto mb-2 text-gray-300" />
            Aún no hay SKUs registrados para este proveedor.
            <p className="text-xs mt-2">Se agregan automáticamente al registrar compras.</p>
          </div>
        ) : (
          <div className="overflow-auto max-h-96">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="text-left p-2">SKU Proveedor</th>
                  <th className="text-left p-2">Producto</th>
                  <th className="text-right p-2">Pack</th>
                  <th className="text-right p-2">Costo</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((s, i) => (
                  <tr key={i} className="border-t">
                    <td className="p-2 font-mono text-xs">{s.sku_proveedor}</td>
                    <td className="p-2">{s.product_name} <span className="text-xs text-gray-500">({s.product_sku})</span></td>
                    <td className="p-2 text-right">{s.factor_pack}</td>
                    <td className="p-2 text-right">${s.last_unit_cost.toLocaleString('es-CO')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cerrar</Button>
      </DialogFooter>
    </Dialog>
  );
}
