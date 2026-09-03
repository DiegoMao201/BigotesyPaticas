'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MapPin, User, Lock, Unlock, Trash2, CalendarDays, Search, MessageCircle, PartyPopper, Home, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import { adminLost, type LostPetAdmin } from '@/lib/api';
import { buildWhatsAppUrl } from '@/lib/phone';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';

function formatAgo(iso: string): string {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days < 1) return 'hoy';
  if (days === 1) return 'ayer';
  return `hace ${days} días`;
}

function daysLeft(iso: string | null): number | null {
  if (!iso) return null;
  return Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000));
}

function whatsappLink(p: LostPetAdmin): string | null {
  const phone = p.reporter_phone || p.contact_phone;
  if (!phone) return null;
  const firstName = (p.reporter_name || '').split(' ')[0] || '';
  const saludo = firstName ? `¡Hola ${firstName}!` : '¡Hola!';
  const msg =
    p.status === 'found'
      ? `${saludo} Soy Angela, de Bigotes y Paticas 🐾 ¡Qué alegría que ${p.pet_name} ya esté en casa! 🎉`
      : `${saludo} Soy Angela, de Bigotes y Paticas 🐾 Vi tu reporte de ${p.pet_name}. Ya lo compartimos con la comunidad — cualquier novedad nos cuentas y lo actualizamos. 💛`;
  return buildWhatsAppUrl(phone, msg);
}

export default function LostPetsModerationPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'active' | 'found' | 'closed'>('active');
  const [search, setSearch] = useState('');
  const [target, setTarget] = useState<LostPetAdmin | null>(null);

  const { data: pets = [], isLoading } = useQuery({
    queryKey: ['admin-lost', tab, search],
    queryFn: () => adminLost.list(tab, search || undefined),
  });
  const invalidate = () => qc.invalidateQueries({ queryKey: ['admin-lost'] });

  const { mutate: setStatus } = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'active' | 'closed' }) => adminLost.setStatus(id, status),
    onSuccess: () => { toast.success('Estado actualizado'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const { mutate: setOutcome, isPending: saving } = useMutation({
    mutationFn: ({ id, outcome, note }: { id: string; outcome: 'found' | 'active'; note?: string }) =>
      adminLost.setOutcome(id, outcome, note),
    onSuccess: (_, vars) => {
      toast.success(vars.outcome === 'found' ? '🎉 ¡Ya está en casa! Se muestra 30 días como historia de éxito' : 'Vuelve a estar como perdido');
      setTarget(null);
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const { mutate: remove } = useMutation({
    mutationFn: (id: string) => adminLost.remove(id),
    onSuccess: () => { toast.success('Reporte eliminado'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mascotas Perdidas</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Reportes de la comunidad. Cuando te avisen que apareció, márcalo <strong>&quot;Ya está en casa&quot;</strong>: la
          publicación pasa a historia de éxito en bigotesypaticas.com durante 30 días y luego se oculta sola.
        </p>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar por nombre de mascota, dueño o teléfono…" className="pl-9" />
      </div>

      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        {([
          { key: 'active', label: '🔴 Perdidos' },
          { key: 'found', label: '🎉 Ya en casa' },
          { key: 'closed', label: 'Cerrados' },
        ] as const).map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${tab === t.key ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">{[...Array(3)].map((_, i) => <Card key={i} className="p-4 animate-pulse h-40" />)}</div>
      ) : pets.length === 0 ? (
        <Card className="p-10 text-center text-gray-500">
          {search ? `Sin resultados para "${search}".` : tab === 'active' ? 'No hay mascotas perdidas ahora mismo. 🎉' : tab === 'found' ? 'Todavía no hay historias de éxito.' : 'No hay reportes cerrados.'}
        </Card>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {pets.map((p) => {
            const wa = whatsappLink(p);
            const left = daysLeft(p.public_until);
            return (
              <Card key={p.id} className="p-0 overflow-hidden flex flex-col">
                <div className="aspect-video bg-red-50 relative overflow-hidden">
                  {p.photos[0] ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={p.photos[0]} alt={p.pet_name} className="h-full w-full object-contain bg-muted" />
                  ) : (
                    <div className="h-full w-full flex items-center justify-center text-4xl">🐾</div>
                  )}
                  <Badge className={`absolute top-2 left-2 ${p.status === 'found' ? 'bg-emerald-500 text-white' : p.status === 'active' ? 'bg-red-500 text-white' : 'bg-gray-500 text-white'}`}>
                    {p.status === 'found' ? '🎉 En casa' : p.status === 'active' ? 'Perdido' : 'Cerrado'}
                  </Badge>
                  {p.status === 'found' && left != null && (
                    <Badge className="absolute top-2 right-2 bg-white/90 text-emerald-800">{left} días visible</Badge>
                  )}
                </div>
                <div className="p-3 flex-1 flex flex-col gap-1.5">
                  <p className="font-semibold text-sm text-gray-900 truncate">{p.pet_name} <span className="text-gray-400 font-normal capitalize">· {p.species}{p.breed ? ` · ${p.breed}` : ''}</span></p>
                  <div className="flex items-center gap-2 text-xs text-gray-500 flex-wrap">
                    <span className="inline-flex items-center gap-1"><CalendarDays className="h-3 w-3" /> {formatAgo(p.created_at)}</span>
                    <a href={`https://www.google.com/maps?q=${p.last_seen_lat},${p.last_seen_lng}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-teal-700">
                      <MapPin className="h-3 w-3" /> Mapa
                    </a>
                    <a href={`https://bigotesypaticas.com/mascotas-perdidas/${p.id}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-teal-700">
                      <ExternalLink className="h-3 w-3" /> Ver en la web
                    </a>
                  </div>
                  {(p.reporter_name || p.reporter_phone) && (
                    <p className="inline-flex items-center gap-1 text-xs text-gray-400"><User className="h-3 w-3" /> {p.reporter_name ?? 'Dueño'} {p.reporter_phone ? `· ${p.reporter_phone}` : ''}</p>
                  )}
                  {p.status === 'found' && (
                    <p className="text-xs text-emerald-700 bg-emerald-50 rounded-lg px-2 py-1">
                      {p.resolution_note || `¡${p.pet_name} ya está en casa! Gracias a todos por ayudar.`}
                    </p>
                  )}

                  {wa && (
                    <a href={wa} target="_blank" rel="noopener noreferrer">
                      <Button size="sm" className="w-full gap-1.5 bg-green-600 hover:bg-green-700 text-white">
                        <MessageCircle className="h-3.5 w-3.5" /> Escribir (soy Angela)
                      </Button>
                    </a>
                  )}

                  <Button size="sm" variant="outline"
                    className={`gap-1.5 ${p.status === 'found' ? 'text-emerald-700 border-emerald-300' : 'border-emerald-300 text-emerald-700 bg-emerald-50 hover:bg-emerald-100'}`}
                    onClick={() => (p.status === 'found' ? setOutcome({ id: p.id, outcome: 'active' }) : setTarget(p))}>
                    {p.status === 'found' ? <><PartyPopper className="h-3.5 w-3.5" /> Quitar &quot;en casa&quot;</> : <><Home className="h-3.5 w-3.5" /> ¡Ya está en casa!</>}
                  </Button>

                  <div className="flex gap-2 mt-auto pt-1">
                    <Button size="sm" variant="outline" className="flex-1 gap-1.5"
                      onClick={() => setStatus({ id: p.id, status: p.status === 'closed' ? 'active' : 'closed' })}>
                      {p.status === 'closed' ? <Unlock className="h-3.5 w-3.5" /> : <Lock className="h-3.5 w-3.5" />}
                      {p.status === 'closed' ? 'Reabrir' : 'Cerrar'}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => { if (confirm(`¿Eliminar el reporte de ${p.pet_name}?`)) remove(p.id); }}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <FoundDialog pet={target} saving={saving} onClose={() => setTarget(null)}
        onConfirm={(note) => target && setOutcome({ id: target.id, outcome: 'found', note })} />
    </div>
  );
}

function FoundDialog({ pet, saving, onClose, onConfirm }: {
  pet: LostPetAdmin | null; saving: boolean; onClose: () => void; onConfirm: (note: string) => void;
}) {
  const [note, setNote] = useState('');
  return (
    <Dialog open={!!pet} onClose={onClose} title={pet ? `🎉 ¡${pet.pet_name} ya está en casa!` : ''}
      description="Se publica como historia de éxito en bigotesypaticas.com durante 30 días, se avisa a los vecinos que estaban pendientes, y luego se oculta sola.">
      <DialogBody>
        <label className="text-xs font-medium text-gray-600">Mensaje para la comunidad (opcional, se muestra en el sitio)</label>
        <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3}
          placeholder={pet ? `Ej: "Gracias a todos por ayudar a que ${pet.pet_name} volviera a su casa. Lo encontró un vecino en el barrio."` : ''}
          className="mt-1 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
        <p className="text-[11px] text-gray-400 mt-1">Si lo dejas vacío se usa: &quot;Gracias a todos los que compartieron y estuvieron pendientes: {pet?.pet_name} volvió a su hogar.&quot;</p>
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cancelar</Button>
        <Button onClick={() => onConfirm(note)} disabled={saving} className="gap-1.5 bg-emerald-600 hover:bg-emerald-700">
          {saving ? 'Guardando…' : 'Confirmar: ya está en casa'}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
