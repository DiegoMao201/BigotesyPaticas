'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { pets, type PetCreate } from '@/lib/api';
import { PET_THEME_COLORS } from '@/lib/pet-store';
import { cn } from '@/lib/utils';

const SPECIES = [
  { value: 'perro', emoji: '🐶', label: 'Perro' },
  { value: 'gato', emoji: '🐱', label: 'Gato' },
  { value: 'conejo', emoji: '🐰', label: 'Conejo' },
  { value: 'hamster', emoji: '🐹', label: 'Hámster' },
  { value: 'ave', emoji: '🐦', label: 'Ave' },
  { value: 'otro', emoji: '🐾', label: 'Otro' },
];

export default function NewPetPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const [form, setForm] = useState<Partial<PetCreate>>({
    species: 'perro',
    color_theme: 'teal',
  });

  const set = (k: keyof PetCreate, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const { mutate, isPending } = useMutation({
    mutationFn: (data: PetCreate) => pets.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['portal-pets'] });
      toast.success('¡Mascota registrada!');
      router.push('/pets');
    },
    onError: (err: any) => toast.error(err.message ?? 'Error al guardar'),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name?.trim()) { toast.error('El nombre es obligatorio'); return; }
    if (!form.species) { toast.error('Selecciona la especie'); return; }
    mutate(form as PetCreate);
  }

  return (
    <div className="p-4 pt-6 flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="p-2 -ml-2 rounded-xl hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h1 className="font-display text-xl font-bold text-foreground">Nueva mascota</h1>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        {/* Nombre */}
        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Nombre *</label>
          <input
            className="input-field"
            placeholder="Nombre de tu mascota"
            value={form.name ?? ''}
            onChange={(e) => set('name', e.target.value)}
            required
          />
        </div>

        {/* Especie */}
        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Especie *</label>
          <div className="grid grid-cols-3 gap-2">
            {SPECIES.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => set('species', s.value)}
                className={cn(
                  'flex flex-col items-center gap-1.5 rounded-xl p-3 border-2 text-xs font-medium transition-all',
                  form.species === s.value
                    ? 'border-primary-700 bg-primary-50 text-primary-700'
                    : 'border-border bg-white text-muted'
                )}
              >
                <span className="text-2xl">{s.emoji}</span>
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Raza */}
        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Raza</label>
          <input
            className="input-field"
            placeholder="Opcional"
            value={form.breed ?? ''}
            onChange={(e) => set('breed', e.target.value)}
          />
        </div>

        {/* Fecha nacimiento + peso */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Nacimiento</label>
            <input
              type="date"
              className="input-field"
              value={form.birth_date ?? ''}
              onChange={(e) => set('birth_date', e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Peso (kg)</label>
            <input
              type="number"
              step="0.1"
              min="0"
              className="input-field"
              placeholder="0.0"
              value={form.weight_kg ?? ''}
              onChange={(e) => set('weight_kg', parseFloat(e.target.value) || undefined)}
            />
          </div>
        </div>

        {/* Alimento */}
        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">
            Marca de alimento
          </label>
          <input
            className="input-field"
            placeholder="Ej: Royal Canin, Purina..."
            value={form.food_brand ?? ''}
            onChange={(e) => set('food_brand', e.target.value)}
          />
        </div>

        {/* Color de tema */}
        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">
            Color de tema
          </label>
          <div className="flex gap-2.5 flex-wrap">
            {Object.entries(PET_THEME_COLORS).map(([key, t]) => (
              <button
                key={key}
                type="button"
                title={t.label}
                onClick={() => set('color_theme', key)}
                className={cn(
                  'h-9 w-9 rounded-full border-4 transition-all',
                  form.color_theme === key ? 'border-foreground scale-110' : 'border-transparent'
                )}
                style={{ backgroundColor: t.primary }}
              />
            ))}
          </div>
        </div>

        {/* Notas */}
        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Notas</label>
          <textarea
            className="input-field min-h-[80px] resize-none"
            placeholder="Alergias, comportamiento, veterinario preferido..."
            value={form.notes ?? ''}
            onChange={(e) => set('notes', e.target.value)}
          />
        </div>

        <button type="submit" disabled={isPending} className="btn-primary">
          {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Registrar mascota'}
        </button>
      </form>
    </div>
  );
}
