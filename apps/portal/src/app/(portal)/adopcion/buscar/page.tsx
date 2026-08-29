'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { adoption, type AdoptionListingInput } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';

export default function SearchAdoptionPage() {
  const router = useRouter();
  const customer = useAuthStore((s) => s.customer);

  const [form, setForm] = useState<Partial<AdoptionListingInput>>({
    post_type: 'want',
    contact_phone: customer?.phone ?? '',
  });
  const [submitting, setSubmitting] = useState(false);

  const set = <K extends keyof AdoptionListingInput>(k: K, v: AdoptionListingInput[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const { mutateAsync: createListing } = useMutation({
    mutationFn: (data: AdoptionListingInput) => adoption.create(data),
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title?.trim()) return toast.error('Escribe un título, ej: "Busco perrito pequeño"');
    if (!form.contact_phone?.trim()) return toast.error('Escribe un teléfono de contacto');

    setSubmitting(true);
    try {
      await createListing(form as AdoptionListingInput);
      toast.success('🐾 Publicado — te pueden contactar directamente');
      router.push('/adopcion');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'No se pudo publicar');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="p-4 pt-6 flex flex-col gap-5 pb-8">
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="p-2 -ml-2 rounded-xl hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h1 className="font-display text-xl font-bold text-foreground">Busco adoptar</h1>
      </div>

      <div className="rounded-2xl p-4 bg-[#E6F5F1] border border-[#bfe6da]">
        <p className="text-xs text-emerald-800 font-medium leading-relaxed">
          🐾 Publica qué tipo de compañero buscas y quien tenga uno disponible te va a contactar.
        </p>
      </div>
      <p className="text-xs text-muted -mt-2">
        Bigotes y Paticas conecta a quienes tienen un animal en adopción con quienes desean adoptar — no
        gestionamos ni somos responsables del proceso de adopción en sí.
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Título *</label>
          <input
            className="input-field"
            placeholder='Ej: "Busco perrito pequeño y tranquilo"'
            value={form.title ?? ''}
            onChange={(e) => set('title', e.target.value)}
            required
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Descripción</label>
          <textarea
            className="input-field"
            rows={3}
            placeholder="Qué buscas, tu experiencia con mascotas, tipo de hogar que ofreces… (opcional)"
            value={form.description ?? ''}
            onChange={(e) => set('description', e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Especie</label>
            <input
              className="input-field"
              placeholder="Perro, gato…"
              value={form.species ?? ''}
              onChange={(e) => set('species', e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Raza preferida</label>
            <input
              className="input-field"
              placeholder="Opcional"
              value={form.breed ?? ''}
              onChange={(e) => set('breed', e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Teléfono de contacto *</label>
          <input
            className="input-field"
            placeholder="300 000 0000"
            value={form.contact_phone ?? ''}
            onChange={(e) => set('contact_phone', e.target.value)}
            required
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3.5 text-sm font-bold text-white shadow-lg transition-all active:scale-95 disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, #2fc4a8, #187f77)', boxShadow: '0 8px 20px rgba(24,127,119,0.3)' }}
        >
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : '🐾 Publicar solicitud'}
        </button>
      </form>
    </div>
  );
}
