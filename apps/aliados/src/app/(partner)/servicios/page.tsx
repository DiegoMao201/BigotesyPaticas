'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Sparkles, Plus, Pencil, Trash2, X } from 'lucide-react';
import { toast } from 'sonner';
import { partner, type PartnerServiceItem } from '@/lib/api';
import { formatCOP } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const CATEGORY_OPTIONS = [
  'consulta', 'vacunacion', 'esterilizacion', 'paseo_30min', 'paseo_60min', 'bano', 'corte', 'otro',
];

const PRICE_TYPE_LABEL: Record<PartnerServiceItem['price_type'], string> = {
  fixed: 'Precio fijo', from: 'Desde', quote: 'Cotización',
};

type FormState = {
  name: string; description: string; duration_min: string; price: string;
  price_type: PartnerServiceItem['price_type']; category: string; requires_pet: boolean;
};

const EMPTY: FormState = {
  name: '', description: '', duration_min: '30', price: '', price_type: 'fixed',
  category: 'consulta', requires_pet: true,
};

function ServiceForm({ editing, onClose }: { editing: PartnerServiceItem | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<FormState>(
    editing
      ? {
          name: editing.name, description: editing.description ?? '',
          duration_min: editing.duration_min ? String(editing.duration_min) : '',
          price: editing.price != null ? String(editing.price) : '',
          price_type: editing.price_type, category: editing.category, requires_pet: editing.requires_pet,
        }
      : EMPTY
  );

  const saveMut = useMutation({
    mutationFn: () => {
      const payload = {
        name: form.name.trim(),
        description: form.description.trim() || null,
        duration_min: form.duration_min ? Number(form.duration_min) : null,
        price: form.price ? Number(form.price) : null,
        price_type: form.price_type,
        category: form.category,
        requires_pet: form.requires_pet,
      };
      return editing ? partner.services.update(editing.id, payload) : partner.services.create(payload);
    },
    onSuccess: () => {
      toast.success(editing ? 'Servicio actualizado' : 'Servicio creado');
      qc.invalidateQueries({ queryKey: ['partner-services'] });
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-display font-bold text-foreground">{editing ? 'Editar servicio' : 'Nuevo servicio'}</h3>
        <button onClick={onClose} className="text-muted hover:text-foreground"><X className="h-4 w-4" /></button>
      </div>

      <div>
        <label className="label-field">Nombre</label>
        <input className="input-field" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Ej. Consulta general" />
      </div>
      <div>
        <label className="label-field">Descripción (opcional)</label>
        <textarea className="input-field resize-none" rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label-field">Categoría</label>
          <select className="input-field" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
            {CATEGORY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="label-field">Duración (min)</label>
          <input type="number" className="input-field" value={form.duration_min} onChange={(e) => setForm({ ...form, duration_min: e.target.value })} placeholder="30" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label-field">Tipo de precio</label>
          <select className="input-field" value={form.price_type} onChange={(e) => setForm({ ...form, price_type: e.target.value as PartnerServiceItem['price_type'] })}>
            <option value="fixed">Fijo</option>
            <option value="from">Desde</option>
            <option value="quote">Cotización</option>
          </select>
        </div>
        {form.price_type !== 'quote' && (
          <div>
            <label className="label-field">Precio (COP)</label>
            <input type="number" className="input-field" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder="50000" />
          </div>
        )}
      </div>
      <label className="flex items-center gap-2 text-sm text-foreground/80">
        <input type="checkbox" checked={form.requires_pet} onChange={(e) => setForm({ ...form, requires_pet: e.target.checked })} />
        Requiere que el cliente traiga a su mascota
      </label>

      <Button onClick={() => saveMut.mutate()} disabled={!form.name.trim() || saveMut.isPending} className="w-full">
        {editing ? 'Guardar cambios' : 'Crear servicio'}
      </Button>
    </div>
  );
}

export default function ServiciosPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<PartnerServiceItem | null>(null);

  const { data, isLoading } = useQuery({ queryKey: ['partner-services'], queryFn: () => partner.services.list() });

  const removeMut = useMutation({
    mutationFn: (id: string) => partner.services.remove(id),
    onSuccess: () => {
      toast.success('Servicio desactivado');
      qc.invalidateQueries({ queryKey: ['partner-services'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const services = (data ?? []).filter((s) => s.is_active);

  function openNew() { setEditing(null); setShowForm(true); }
  function openEdit(s: PartnerServiceItem) { setEditing(s); setShowForm(true); }
  function closeForm() { setShowForm(false); setEditing(null); }

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-2xl font-bold text-foreground flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary-700" /> Servicios
          </h1>
          <p className="text-muted text-sm mt-1">Lo que ofreces a los clientes de Bigotes y Paticas.</p>
        </div>
        {!showForm && (
          <Button onClick={openNew}><Plus className="h-4 w-4" /> Nuevo servicio</Button>
        )}
      </div>

      {showForm && <ServiceForm editing={editing} onClose={closeForm} />}

      {isLoading && <p className="text-sm text-muted">Cargando…</p>}

      {!isLoading && services.length === 0 && !showForm && (
        <div className="card text-center py-10 text-muted text-sm">
          Todavía no tienes servicios. Crea el primero para que los clientes puedan agendar contigo.
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {services.map((s) => (
          <div key={s.id} className="card flex flex-col gap-2">
            <div className="flex items-start justify-between gap-2">
              <p className="font-semibold text-foreground">{s.name}</p>
              <Badge>{s.category}</Badge>
            </div>
            {s.description && <p className="text-sm text-muted">{s.description}</p>}
            <div className="flex items-center justify-between mt-1">
              <p className="text-sm text-foreground/70">
                {s.duration_min ? `${s.duration_min} min · ` : ''}
                {s.price_type === 'quote' ? 'Cotización' : `${PRICE_TYPE_LABEL[s.price_type]} ${s.price != null ? formatCOP(s.price) : ''}`}
              </p>
            </div>
            <div className="flex gap-2 pt-2 border-t border-border">
              <Button size="sm" variant="outline" onClick={() => openEdit(s)}><Pencil className="h-3.5 w-3.5" /> Editar</Button>
              <Button size="sm" variant="danger" onClick={() => removeMut.mutate(s.id)}><Trash2 className="h-3.5 w-3.5" /> Desactivar</Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
