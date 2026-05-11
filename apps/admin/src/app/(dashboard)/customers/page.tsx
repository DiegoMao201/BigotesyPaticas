'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Users, Phone, Mail, MapPin, Plus, Pencil } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { cn, formatCurrency } from '@/lib/utils';
import { customers, type Customer } from '@/lib/api';

const RFM_BADGE: Record<string, { label: string; cls: string }> = {
  champion: { label: 'Campeón', cls: 'bg-emerald-100 text-emerald-800' },
  loyal: { label: 'Leal', cls: 'bg-blue-100 text-blue-800' },
  potential: { label: 'Potencial', cls: 'bg-violet-100 text-violet-800' },
  at_risk: { label: 'En riesgo', cls: 'bg-amber-100 text-amber-800' },
  lost: { label: 'Perdido', cls: 'bg-rose-100 text-rose-800' },
};

function RfmBadge({ segment }: { segment: string | null }) {
  if (!segment) return null;
  const b = RFM_BADGE[segment] ?? { label: segment, cls: 'bg-muted text-muted-foreground' };
  return (
    <span className={cn('px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide', b.cls)}>
      {b.label}
    </span>
  );
}

type CustomerFormData = {
  full_name: string;
  email: string;
  phone: string;
  city: string;
  document_id: string;
  notes: string;
};

function CustomerForm({
  initial,
  onSubmit,
  loading,
}: {
  initial?: Customer;
  onSubmit: (d: CustomerFormData) => void;
  loading: boolean;
}) {
  const [form, setForm] = useState<CustomerFormData>({
    full_name: initial?.full_name || '',
    email: initial?.email || '',
    phone: initial?.phone || '',
    city: initial?.city || '',
    document_id: initial?.document_id || '',
    notes: initial?.notes || '',
  });
  const set = (k: keyof CustomerFormData, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(form);
      }}
    >
      <DialogBody className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs font-medium mb-1 block">Nombre completo *</label>
            <Input required value={form.full_name} onChange={(e) => set('full_name', e.target.value)} placeholder="Juan García" />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Email</label>
            <Input type="email" value={form.email} onChange={(e) => set('email', e.target.value)} placeholder="email@ejemplo.com" />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Teléfono</label>
            <Input value={form.phone} onChange={(e) => set('phone', e.target.value)} placeholder="300 000 0000" />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Ciudad</label>
            <Input value={form.city} onChange={(e) => set('city', e.target.value)} placeholder="Dosquebradas" />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Documento (CC/NIT)</label>
            <Input value={form.document_id} onChange={(e) => set('document_id', e.target.value)} placeholder="1234567890" />
          </div>
          <div className="col-span-2">
            <label className="text-xs font-medium mb-1 block">Notas</label>
            <textarea
              value={form.notes}
              onChange={(e) => set('notes', e.target.value)}
              rows={2}
              placeholder="Notas internas…"
              className="w-full px-3 py-2 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>
      </DialogBody>
      <DialogFooter>
        <Button type="submit" disabled={loading || !form.full_name}>
          {loading ? 'Guardando…' : initial ? 'Guardar cambios' : 'Crear cliente'}
        </Button>
      </DialogFooter>
    </form>
  );
}

export default function CustomersPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [editCustomer, setEditCustomer] = useState<Customer | null>(null);
  const [openCreate, setOpenCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['customers', q, page],
    queryFn: () => customers.list({ q: q || undefined, page, page_size: 25 }),
    staleTime: 30_000,
  });

  const createMut = useMutation({
    mutationFn: (d: CustomerFormData) => customers.create({ ...d, email: d.email || undefined, phone: d.phone || undefined, city: d.city || undefined, document_id: d.document_id || undefined, notes: d.notes || undefined }),
    onSuccess: () => { toast.success('Cliente creado'); qc.invalidateQueries({ queryKey: ['customers'] }); setOpenCreate(false); },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, d }: { id: string; d: CustomerFormData }) => customers.update!(id, { ...d, email: d.email || undefined, phone: d.phone || undefined, city: d.city || undefined, document_id: d.document_id || undefined, notes: d.notes || undefined }),
    onSuccess: () => { toast.success('Cliente actualizado'); qc.invalidateQueries({ queryKey: ['customers'] }); setEditCustomer(null); },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight">Clientes</h1>
          <p className="text-muted-foreground mt-1 text-sm">CRM con segmentación RFM — {data?.total ?? '…'} registros</p>
        </div>
        <Button onClick={() => setOpenCreate(true)}>
          <Plus className="h-4 w-4" /> Nuevo cliente
        </Button>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Nombre, email, teléfono…"
          className="pl-9"
          value={q}
          onChange={(e) => { setQ(e.target.value); setPage(1); }}
        />
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="divide-y divide-border/40">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="flex items-center gap-4 p-4">
                  <div className="w-9 h-9 rounded-full bg-muted/40 animate-pulse" />
                  <div className="space-y-2 flex-1">
                    <div className="h-4 w-48 bg-muted/40 animate-pulse rounded" />
                    <div className="h-3 w-32 bg-muted/30 animate-pulse rounded" />
                  </div>
                </div>
              ))}
            </div>
          ) : (data?.items?.length ?? 0) === 0 ? (
            <div className="py-16 text-center text-muted-foreground">
              <Users className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">{q ? 'Sin resultados para esa búsqueda' : 'No hay clientes registrados'}</p>
            </div>
          ) : (
            <div className="divide-y divide-border/40">
              {data!.items.map((c: Customer) => (
                <div key={c.id} className="flex items-center gap-4 px-4 py-3 hover:bg-accent/30 transition-colors group">
                  <div className="w-9 h-9 rounded-full gradient-brand flex items-center justify-center text-white text-sm font-bold shrink-0">
                    {(c.full_name ?? '?').charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{c.full_name}</span>
                      <RfmBadge segment={c.rfm_segment} />
                    </div>
                    <div className="flex items-center gap-3 mt-0.5 text-xs text-muted-foreground">
                      {c.email && <span className="flex items-center gap-1"><Mail className="h-3 w-3" />{c.email}</span>}
                      {c.phone && <span className="flex items-center gap-1"><Phone className="h-3 w-3" />{c.phone}</span>}
                      {c.city && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{c.city}</span>}
                    </div>
                  </div>
                  {c.rfm_monetary != null && (
                    <div className="text-right text-sm">
                      <div className="font-semibold text-brand-700">{formatCurrency(c.rfm_monetary)}</div>
                      <div className="text-xs text-muted-foreground">acumulado</div>
                    </div>
                  )}
                  <button
                    onClick={() => setEditCustomer(c)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-muted text-muted-foreground transition-opacity"
                    title="Editar"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </CardContent>

        {(data?.total ?? 0) > 25 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border/40 text-sm text-muted-foreground">
            <span>Página {page} de {Math.ceil((data?.total ?? 0) / 25)}</span>
            <div className="flex gap-2">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 rounded border border-border hover:bg-accent/50 disabled:opacity-40">Anterior</button>
              <button onClick={() => setPage((p) => p + 1)} disabled={page * 25 >= (data?.total ?? 0)} className="px-3 py-1 rounded border border-border hover:bg-accent/50 disabled:opacity-40">Siguiente</button>
            </div>
          </div>
        )}
      </Card>

      <Dialog open={openCreate} onClose={() => setOpenCreate(false)} title="Nuevo cliente" size="md">
        <CustomerForm onSubmit={(d) => createMut.mutate(d)} loading={createMut.isPending} />
      </Dialog>

      <Dialog open={!!editCustomer} onClose={() => setEditCustomer(null)} title="Editar cliente" size="md">
        {editCustomer && (
          <CustomerForm
            initial={editCustomer}
            onSubmit={(d) => updateMut.mutate({ id: editCustomer.id, d })}
            loading={updateMut.isPending}
          />
        )}
      </Dialog>
    </div>
  );
}

