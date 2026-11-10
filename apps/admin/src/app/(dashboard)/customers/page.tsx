'use client';

import { useState } from 'react';
import { useBorrador, descartarBorrador, leerBorrador, useClavesConBorrador } from '@/lib/borradores';
import { PendienteAviso } from '@/components/PendienteAviso';
import { CustomerForm, aPayload, type CustomerFormData } from '@/components/CustomerForm';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Users, Phone, Mail, MapPin, Plus, Pencil } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/card';
import { faltantes, etiquetaFaltantes } from '@/components/DatosFaltantes';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { cn, formatCurrency } from '@/lib/utils';
import { customers, type Customer } from '@/lib/api';
import { InviteToPortalModal } from '@/components/InviteToPortalModal';

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

export default function CustomersPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [faltan, setFaltan] = useState<'' | 'cualquiera' | 'correo' | 'cedula' | 'celular' | 'direccion'>('');
  const [editCustomer, setEditCustomer] = useBorrador<Customer | null>('clientes:editando', null);
  const [inviteCustomer, setInviteCustomer] = useState<Customer | null>(null);
  const [openCreate, setOpenCreate] = useBorrador('clientes:nuevo:abierto', false);

  // Lo que quedó a medias con el diálogo cerrado: si no se muestra aquí, el menú dice
  // "en curso" y no hay cómo encontrarlo (10-nov-2026).
  const pendientes = useClavesConBorrador('clientes');
  const nuevoPendiente = !openCreate && pendientes.some((k) => k.startsWith('clientes:nuevo:form'));
  const edicionesPendientes = [...new Set(
    pendientes.filter((k) => k.startsWith('clientes:form:')).map((k) => k.split(':')[2]),
  )].filter((id) => id !== editCustomer?.id);
  async function retomarEdicion(id: string) {
    try {
      setEditCustomer(await customers.get(id));
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  const { data, isLoading } = useQuery({
    queryKey: ['customers', q, page, faltan],
    queryFn: () => customers.list({ q: q || undefined, page, page_size: 25, faltan: faltan || undefined }),
    staleTime: 30_000,
  });

  const createMut = useMutation({
    mutationFn: (d: CustomerFormData) => customers.create(aPayload(d)),
    onSuccess: () => { toast.success('Cliente creado'); qc.invalidateQueries({ queryKey: ['customers'] }); descartarBorrador('clientes:nuevo'); },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, d }: { id: string; d: CustomerFormData }) => customers.update(id, aPayload(d)),
    onSuccess: (_r, v) => { toast.success('Cliente actualizado'); qc.invalidateQueries({ queryKey: ['customers'] }); descartarBorrador(`clientes:form:${v.id}`); setEditCustomer(null); },
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

      {nuevoPendiente && (
        <PendienteAviso
          texto={<>Tienes un <b>cliente nuevo a medio crear</b>{leerBorrador<CustomerFormData>('clientes:nuevo:form')?.full_name ? <>: <b>{leerBorrador<CustomerFormData>('clientes:nuevo:form')!.full_name}</b></> : ''}.</>}
          onContinuar={() => setOpenCreate(true)}
          onDescartar={() => descartarBorrador('clientes:nuevo')}
        />
      )}
      {edicionesPendientes.map((id) => (
        <PendienteAviso
          key={id}
          texto={<>Cambios sin guardar en el cliente <b>{leerBorrador<CustomerFormData>(`clientes:form:${id}`)?.full_name || 'sin nombre'}</b>.</>}
          onContinuar={() => retomarEdicion(id)}
          onDescartar={() => descartarBorrador(`clientes:form:${id}`)}
        />
      ))}

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative max-w-sm flex-1 min-w-[220px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Nombre, email, teléfono…"
            className="pl-9"
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1); }}
          />
        </div>
        {/* Base lista para facturación electrónica: ver de un vistazo a quién le falta qué. */}
        <div className="flex flex-wrap gap-1">
          {([
            ['', 'Todos'], ['cualquiera', 'Incompletos'], ['correo', 'Sin correo'], ['cedula', 'Sin cédula'], ['celular', 'Sin celular'], ['direccion', 'Sin dirección'],
          ] as const).map(([k, label]) => (
            <button
              key={k}
              onClick={() => { setFaltan(k); setPage(1); }}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${faltan === k ? 'bg-brand-500 text-white border-brand-500' : 'border-border text-muted-foreground hover:bg-muted'}`}
            >
              {label}
            </button>
          ))}
        </div>
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
                <div key={c.id} className="flex items-start sm:items-center gap-3 px-4 py-3 hover:bg-accent/30 transition-colors group">
                  <div className="w-9 h-9 rounded-full gradient-brand flex items-center justify-center text-white text-sm font-bold shrink-0">
                    {(c.full_name ?? '?').charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm">{c.full_name}</span>
                      <RfmBadge segment={c.rfm_segment} />
                      {faltantes(c).length > 0 && (
                        <span className="text-[11px] rounded-full bg-amber-100 text-amber-800 px-2 py-0.5">Falta: {etiquetaFaltantes(c)}</span>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-3 mt-0.5 text-xs text-muted-foreground">
                      {c.email && <span className="flex items-center gap-1"><Mail className="h-3 w-3" />{c.email}</span>}
                      {c.phone && <span className="flex items-center gap-1"><Phone className="h-3 w-3" />{c.phone}</span>}
                      {c.city && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{c.city}</span>}
                      {c.pet_name && <span className="flex items-center gap-1">Mascota: {c.pet_name}{c.pet_type ? ` (${c.pet_type})` : ''}</span>}
                    </div>
                  </div>
                  {c.rfm_monetary != null && (
                    <div className="text-right text-sm hidden sm:block">
                      <div className="font-semibold text-brand-700">{formatCurrency(c.rfm_monetary)}</div>
                      <div className="text-xs text-muted-foreground">acumulado</div>
                    </div>
                  )}
                  <button
                    onClick={() => setInviteCustomer(c)}
                    className="p-2 rounded border border-teal-200 hover:bg-teal-50 text-teal-600 transition-colors shrink-0"
                    title="Invitar al portal"
                  >
                    📨
                  </button>
                  <button
                    onClick={() => setEditCustomer(c)}
                    className="p-2 rounded border border-border hover:bg-muted text-muted-foreground transition-colors shrink-0"
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

      {inviteCustomer && (
        <InviteToPortalModal
          customer={inviteCustomer}
          open={!!inviteCustomer}
          onClose={() => setInviteCustomer(null)}
        />
      )}
    </div>
  );
}

