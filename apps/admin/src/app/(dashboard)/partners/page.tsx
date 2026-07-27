'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Handshake, CheckCircle2, XCircle, ShieldCheck, MapPin, Phone, Mail, Star,
} from 'lucide-react';
import { toast } from 'sonner';
import { adminPartners, type AdminPartner } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const TYPE_LABEL: Record<AdminPartner['partner_type'], string> = {
  vet: '🩺 Veterinaria',
  walker: '🐕 Paseador',
  shelter: '🏠 Refugio',
  groomer: '✂️ Peluquería',
};

const TABS = [
  { value: 'pending', label: 'Pendientes' },
  { value: 'published', label: 'Publicados' },
  { value: 'all', label: 'Todos' },
] as const;

function PartnerCard({ partner }: { partner: AdminPartner }) {
  const qc = useQueryClient();

  const approveMut = useMutation({
    mutationFn: () => adminPartners.approve(partner.id),
    onSuccess: () => {
      toast.success(`${partner.business_name} aprobado — ya aparece en el directorio`);
      qc.invalidateQueries({ queryKey: ['admin-partners'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const rejectMut = useMutation({
    mutationFn: () => adminPartners.reject(partner.id),
    onSuccess: () => {
      toast.success(`${partner.business_name} rechazado`);
      qc.invalidateQueries({ queryKey: ['admin-partners'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const verifyMut = useMutation({
    mutationFn: () => adminPartners.toggleVerified(partner.id),
    onSuccess: (res) => {
      toast.success(res.verified ? '✅ Marcado como verificado' : 'Verificación retirada');
      qc.invalidateQueries({ queryKey: ['admin-partners'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Card className="p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="font-semibold text-foreground truncate">{partner.business_name}</p>
            {partner.is_verified && (
              <Badge variant="success"><ShieldCheck className="w-3 h-3" /> Verificado</Badge>
            )}
            <Badge variant={partner.is_published ? 'success' : 'warning'}>
              {partner.is_published ? 'Publicado' : 'Pendiente'}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">{TYPE_LABEL[partner.partner_type]} · {partner.legal_name}</p>
        </div>
        {partner.rating_count > 0 && (
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-amber-600 shrink-0">
            <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" /> {partner.rating_avg.toFixed(1)} ({partner.rating_count})
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5 shrink-0" /> {partner.address ? `${partner.address}, ` : ''}{partner.city}</span>
        {partner.phone && <span className="inline-flex items-center gap-1.5"><Phone className="w-3.5 h-3.5 shrink-0" /> {partner.phone}</span>}
        {partner.email && <span className="inline-flex items-center gap-1.5 col-span-2"><Mail className="w-3.5 h-3.5 shrink-0" /> {partner.email}</span>}
        <span className="col-span-2">NIT: {partner.document_id}</span>
      </div>

      {partner.bio && <p className="text-sm text-foreground/80">{partner.bio}</p>}

      <div className="flex items-center gap-2 pt-1 border-t border-border">
        {!partner.is_published ? (
          <>
            <Button size="sm" onClick={() => approveMut.mutate()} disabled={approveMut.isPending}>
              <CheckCircle2 className="w-4 h-4" /> Aprobar
            </Button>
            <Button size="sm" variant="outline" onClick={() => rejectMut.mutate()} disabled={rejectMut.isPending}>
              <XCircle className="w-4 h-4" /> Rechazar
            </Button>
          </>
        ) : (
          <Button size="sm" variant="outline" onClick={() => verifyMut.mutate()} disabled={verifyMut.isPending}>
            <ShieldCheck className="w-4 h-4" /> {partner.is_verified ? 'Quitar verificación' : 'Marcar verificado'}
          </Button>
        )}
      </div>
    </Card>
  );
}

export default function PartnersPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]['value']>('pending');

  const { data, isLoading } = useQuery({
    queryKey: ['admin-partners', tab],
    queryFn: () => adminPartners.list(tab),
  });

  const partners = data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <Handshake className="w-6 h-6 text-primary-700" /> Aliados
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Veterinarias, paseadores, refugios y peluquerías registrados en la plataforma
          </p>
        </div>
      </div>

      <div className="flex gap-2 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value)}
            className={
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ' +
              (tab === t.value
                ? 'border-primary-700 text-primary-700'
                : 'border-transparent text-muted-foreground hover:text-foreground')
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      {!isLoading && partners.length === 0 && (
        <Card className="p-10 text-center text-muted-foreground text-sm">
          No hay aliados {tab === 'pending' ? 'pendientes de aprobación' : tab === 'published' ? 'publicados todavía' : 'registrados todavía'}.
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {partners.map((p) => (
          <PartnerCard key={p.id} partner={p} />
        ))}
      </div>
    </div>
  );
}
