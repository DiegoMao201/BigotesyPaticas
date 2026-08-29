'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MapPin, Heart, User, Lock, Unlock, Trash2, CalendarDays, Search, MessageCircle, PartyPopper } from 'lucide-react';
import { toast } from 'sonner';
import { adminAdoption, type AdoptionListing } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';

function formatAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diffMs / 86_400_000);
  if (days < 1) return 'hoy';
  if (days === 1) return 'ayer';
  return `hace ${days} días`;
}

function whatsappWelcomeLink(l: AdoptionListing): string | null {
  if (!l.reporter_phone) return null;
  const digits = l.reporter_phone.replace(/\D/g, '');
  const withCountry = digits.startsWith('57') ? digits : `57${digits}`;
  const firstName = (l.reporter_name || '').split(' ')[0] || '';
  const saludo = firstName ? `¡Hola ${firstName}!` : '¡Hola!';
  const msg =
    l.post_type === 'want'
      ? `${saludo} Soy Angela, de Bigotes y Paticas 🐾 Vi tu mensaje de que estás buscando adoptar. Quiero que sepas que desde acá vamos a hacer lo posible para que un peludito encuentre un hogar, y sé que tú lo vas a hacer muy feliz. Cualquier cosa que necesites, contá con nosotros 💛`
      : `${saludo} Soy Angela, de Bigotes y Paticas 🐾 Vi que quieres dar a tu peludito en adopción. Gracias por confiar en que le ayudemos a encontrar un buen hogar — vamos a hacer lo posible para conectarlo con la familia correcta 💛`;
  return `https://wa.me/${withCountry}?text=${encodeURIComponent(msg)}`;
}

export default function AdoptionModerationPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'open' | 'closed'>('open');
  const [typeFilter, setTypeFilter] = useState<'all' | 'offer' | 'want'>('all');
  const [search, setSearch] = useState('');
  const [outcomeTarget, setOutcomeTarget] = useState<AdoptionListing | null>(null);

  const { data: listings = [], isLoading } = useQuery({
    queryKey: ['admin-adoption', tab, search],
    queryFn: () => adminAdoption.list(tab, search || undefined),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ['admin-adoption'] });

  const { mutate: setStatus } = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'open' | 'closed' }) => adminAdoption.setStatus(id, status),
    onSuccess: () => {
      toast.success('Estado actualizado');
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const { mutate: setOutcome, isPending: savingOutcome } = useMutation({
    mutationFn: ({ id, outcome, note }: { id: string; outcome: 'pending' | 'matched'; note?: string }) =>
      adminAdoption.setOutcome(id, outcome, note),
    onSuccess: (_, vars) => {
      toast.success(vars.outcome === 'matched' ? '🎉 Marcada como historia de éxito' : 'Se quitó de historias de éxito');
      setOutcomeTarget(null);
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const { mutate: remove } = useMutation({
    mutationFn: (id: string) => adminAdoption.remove(id),
    onSuccess: () => {
      toast.success('Publicación eliminada');
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const filtered = typeFilter === 'all' ? listings : listings.filter((l) => l.post_type === typeFilter);

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Foro de Adopción</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Publicaciones de clientes que dan animales en adopción o buscan adoptar, desde el portal o el foro rápido.
        </p>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nombre o teléfono…"
          className="pl-9"
        />
      </div>

      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
          {(['open', 'closed'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                tab === t ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t === 'open' ? 'Abiertas' : 'Cerradas'}
            </button>
          ))}
        </div>
        <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
          {([
            { key: 'all', label: 'Todas' },
            { key: 'offer', label: '🏠 En adopción' },
            { key: 'want', label: '🔍 Buscan adoptar' },
          ] as const).map((t) => (
            <button
              key={t.key}
              onClick={() => setTypeFilter(t.key)}
              className={`px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                typeFilter === t.key ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <Card key={i} className="p-4 animate-pulse h-40" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card className="p-10 text-center text-gray-500">
          {search ? `Sin resultados para "${search}".` : `No hay publicaciones ${tab === 'open' ? 'abiertas' : 'cerradas'} todavía.`}
        </Card>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {filtered.map((l) => {
            const waLink = whatsappWelcomeLink(l);
            return (
              <Card key={l.id} className="p-0 overflow-hidden flex flex-col">
                <div className="aspect-video bg-teal-50 relative overflow-hidden">
                  {l.photos[0] ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={l.photos[0]} alt={l.title} className="h-full w-full object-cover" />
                  ) : (
                    <div className="h-full w-full flex items-center justify-center text-teal-300">
                      <Heart className="h-8 w-8" />
                    </div>
                  )}
                  <Badge className="absolute top-2 left-2 bg-white/90 text-teal-800">
                    {l.post_type === 'offer' ? '🏠 En adopción' : '🔍 Busca adoptar'}
                  </Badge>
                  {l.outcome === 'matched' && (
                    <Badge className="absolute top-2 right-2 bg-emerald-500 text-white">🎉 Adoptado</Badge>
                  )}
                </div>
                <div className="p-3 flex-1 flex flex-col gap-1.5">
                  <p className="font-semibold text-sm text-gray-900 truncate">{l.title}</p>
                  <div className="flex items-center gap-2 text-xs text-gray-500 flex-wrap">
                    <span className="inline-flex items-center gap-1"><CalendarDays className="h-3 w-3" /> {formatAgo(l.created_at)}</span>
                    {l.address && <span className="inline-flex items-center gap-1 truncate"><MapPin className="h-3 w-3 shrink-0" /> {l.address}</span>}
                  </div>
                  {l.reporter_name && (
                    <p className="inline-flex items-center gap-1 text-xs text-gray-400">
                      <User className="h-3 w-3" /> {l.reporter_name} {l.reporter_phone ? `· ${l.reporter_phone}` : ''}
                    </p>
                  )}
                  {l.outcome === 'matched' && l.outcome_note && (
                    <p className="text-xs text-emerald-700 bg-emerald-50 rounded-lg px-2 py-1">{l.outcome_note}</p>
                  )}

                  {waLink && (
                    <a href={waLink} target="_blank" rel="noopener noreferrer">
                      <Button size="sm" className="w-full gap-1.5 bg-green-600 hover:bg-green-700 text-white">
                        <MessageCircle className="h-3.5 w-3.5" /> Escribir (soy Angela)
                      </Button>
                    </a>
                  )}

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className={`flex-1 gap-1.5 ${l.outcome === 'matched' ? 'text-emerald-700 border-emerald-300' : ''}`}
                      onClick={() =>
                        l.outcome === 'matched'
                          ? setOutcome({ id: l.id, outcome: 'pending' })
                          : setOutcomeTarget(l)
                      }
                    >
                      <PartyPopper className="h-3.5 w-3.5" />
                      {l.outcome === 'matched' ? 'Quitar éxito' : 'Encontró hogar'}
                    </Button>
                  </div>

                  <div className="flex gap-2 mt-auto pt-1">
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1 gap-1.5"
                      onClick={() => setStatus({ id: l.id, status: l.status === 'open' ? 'closed' : 'open' })}
                    >
                      {l.status === 'open' ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}
                      {l.status === 'open' ? 'Cerrar' : 'Reabrir'}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => remove(l.id)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <OutcomeDialog
        listing={outcomeTarget}
        saving={savingOutcome}
        onClose={() => setOutcomeTarget(null)}
        onConfirm={(note) => outcomeTarget && setOutcome({ id: outcomeTarget.id, outcome: 'matched', note })}
      />
    </div>
  );
}

function OutcomeDialog({
  listing,
  saving,
  onClose,
  onConfirm,
}: {
  listing: AdoptionListing | null;
  saving: boolean;
  onClose: () => void;
  onConfirm: (note: string) => void;
}) {
  const [note, setNote] = useState('');

  return (
    <Dialog
      open={!!listing}
      onClose={onClose}
      title="🎉 Marcar como historia de éxito"
      description={listing ? `"${listing.title}" se mostrará como éxito en la página pública antes de cerrarse.` : undefined}
    >
      <DialogBody>
        <label className="text-xs font-medium text-gray-600">¿Cómo fue? (opcional, se muestra en el sitio)</label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          placeholder='Ej: "¡Encontró un hogar en Dosquebradas!"'
          className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cancelar</Button>
        <Button onClick={() => onConfirm(note)} disabled={saving} className="gap-1.5 bg-emerald-600 hover:bg-emerald-700">
          {saving ? 'Guardando…' : 'Confirmar éxito'}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
