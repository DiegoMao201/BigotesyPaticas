'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Store, Save } from 'lucide-react';
import { toast } from 'sonner';
import { partner } from '@/lib/api';
import { useAuth } from '@/lib/auth-store';
import { LocationPicker } from '@/components/maps/LocationPicker';
import { Button } from '@/components/ui/button';

export default function PerfilPage() {
  const qc = useQueryClient();
  const updatePartner = useAuth((s) => s.updatePartner);
  const { data, isLoading } = useQuery({ queryKey: ['partner-profile'], queryFn: () => partner.profile.get() });

  const [form, setForm] = useState({
    business_name: '', phone: '', whatsapp: '', address: '', city: '', bio: '',
    lat: null as number | null, lng: null as number | null,
  });

  useEffect(() => {
    if (!data) return;
    setForm({
      business_name: data.business_name, phone: data.phone ?? '', whatsapp: data.whatsapp ?? '',
      address: data.address ?? '', city: data.city, bio: data.bio ?? '', lat: data.lat, lng: data.lng,
    });
  }, [data]);

  const saveMut = useMutation({
    mutationFn: () =>
      partner.profile.update({
        business_name: form.business_name,
        phone: form.phone || undefined,
        whatsapp: form.whatsapp || undefined,
        address: form.address || undefined,
        city: form.city,
        bio: form.bio || undefined,
        lat: form.lat ?? undefined,
        lng: form.lng ?? undefined,
      }),
    onSuccess: (updated) => {
      toast.success('Perfil actualizado');
      updatePartner({ business_name: updated.business_name });
      qc.invalidateQueries({ queryKey: ['partner-profile'] });
      qc.invalidateQueries({ queryKey: ['partner-dashboard'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (isLoading || !data) {
    return <p className="text-sm text-muted">Cargando…</p>;
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground flex items-center gap-2">
          <Store className="h-6 w-6 text-primary-700" /> Mi perfil
        </h1>
        <p className="text-muted text-sm mt-1">
          Así es como te ven los clientes en el directorio de aliados.
        </p>
      </div>

      <div className="card space-y-4">
        <p className="text-xs text-muted">
          NIT <strong>{data.document_id}</strong> y tipo de negocio no se pueden editar aquí — escríbenos si necesitas corregirlos.
        </p>

        <div>
          <label className="label-field">Nombre comercial</label>
          <input className="input-field" value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label-field">Teléfono</label>
            <input className="input-field" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
          <div>
            <label className="label-field">WhatsApp</label>
            <input className="input-field" value={form.whatsapp} onChange={(e) => setForm({ ...form, whatsapp: e.target.value })} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label-field">Ciudad</label>
            <input className="input-field" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
          </div>
          <div>
            <label className="label-field">Dirección</label>
            <input className="input-field" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </div>
        </div>
        <div>
          <label className="label-field">Ubicación en el mapa</label>
          <LocationPicker lat={form.lat} lng={form.lng} onChange={(lat, lng) => setForm({ ...form, lat, lng })} />
        </div>
        <div>
          <label className="label-field">Sobre tu negocio</label>
          <textarea className="input-field resize-none" rows={3} value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} />
        </div>

        <Button onClick={() => saveMut.mutate()} disabled={saveMut.isPending} className="w-full">
          <Save className="h-4 w-4" /> Guardar cambios
        </Button>
      </div>
    </div>
  );
}
