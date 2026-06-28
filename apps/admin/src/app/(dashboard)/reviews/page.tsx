'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Star, CheckCircle, XCircle, MessageSquare, Package, User, MapPin, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { formatCurrency } from '@/lib/utils';

// ── Tipos ────────────────────────────────────────────────────────────────────

interface ReviewItem {
  id: string;
  product_id: string;
  product_name: string;
  product_sku: string | null;
  product_image: string | null;
  customer_id: string;
  customer_name: string;
  customer_phone: string | null;
  rating: number;
  title: string | null;
  comment: string | null;
  photo_urls: string[];
  pet_name: string | null;
  status: string;
  is_verified_purchase: boolean;
  helpful_count: number;
  admin_reply: string | null;
  admin_reply_at: string | null;
  created_at: string;
  points_awarded: number;
}

// ── Star display ─────────────────────────────────────────────────────────────

function Stars({ rating }: { rating: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <Star
          key={s}
          className={`w-4 h-4 ${s <= rating ? 'fill-amber-400 text-amber-400' : 'text-gray-200'}`}
        />
      ))}
    </div>
  );
}

// ── Reply modal ───────────────────────────────────────────────────────────────

const REPLY_TEMPLATES = {
  '5': '¡Gracias por tu calificación! Nos alegra mucho que tú y tu mascota estén felices con el producto. ¡Hasta pronto! 🐾',
  '4': '¡Gracias por tu reseña! Nos alegra que hayas tenido una buena experiencia. Si hay algo en lo que podamos mejorar, cuéntanos.',
  '3': 'Gracias por compartir tu experiencia. Tomaremos en cuenta tu opinión para seguir mejorando. ¡Cualquier duda, estamos aquí!',
  '2': 'Lamentamos que tu experiencia no haya sido la esperada. Por favor contáctanos al WhatsApp para resolver tu caso de inmediato.',
  '1': 'Sentimos mucho lo que ocurrió. Queremos solucionarlo — escríbenos al WhatsApp +57 320 687 6633 y lo atendemos con prioridad.',
};

function ReplyModal({ review, onClose }: { review: ReviewItem; onClose: () => void }) {
  const [reply, setReply] = useState(review.admin_reply ?? REPLY_TEMPLATES[String(review.rating) as keyof typeof REPLY_TEMPLATES] ?? '');
  const qc = useQueryClient();
  const mut = useMutation({
    mutationFn: () => api(`/admin/reviews/${review.id}/reply`, { method: 'POST', body: JSON.stringify({ reply }) }),
    onSuccess: () => { toast.success('Respuesta publicada'); qc.invalidateQueries({ queryKey: ['admin-reviews'] }); onClose(); },
    onError: (e: Error) => toast.error(e.message),
  });
  return (
    <Dialog open onClose={onClose} title={`Responder a ${review.customer_name}`}>
      <DialogBody>
        <div className="mb-3 p-3 rounded-xl bg-gray-50 border text-sm text-gray-700 italic">
          "{review.comment || '(sin comentario)'}"
        </div>
        <label className="text-xs font-semibold text-muted mb-1 block">Tu respuesta pública</label>
        <textarea
          rows={5}
          value={reply}
          onChange={(e) => setReply(e.target.value)}
          className="w-full rounded-xl border border-border p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-600/20"
          placeholder="Escribe una respuesta..."
        />
        <div className="flex gap-2 flex-wrap mt-2">
          {Object.entries(REPLY_TEMPLATES).map(([rating, tpl]) => (
            <button
              key={rating}
              type="button"
              onClick={() => setReply(tpl)}
              className="text-xs px-2 py-1 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors"
            >
              {'⭐'.repeat(Number(rating))}
            </button>
          ))}
        </div>
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cancelar</Button>
        <Button onClick={() => mut.mutate()} disabled={mut.isPending || !reply.trim()}>
          Publicar respuesta
        </Button>
      </DialogFooter>
    </Dialog>
  );
}

// ── Review card ───────────────────────────────────────────────────────────────

function ReviewCard({ review, onModerate }: {
  review: ReviewItem;
  onModerate: (id: string, action: 'approve' | 'reject', notes?: string) => void;
}) {
  const [showReply, setShowReply] = useState(false);
  const statusColor = {
    pending: 'warning',
    approved: 'success',
    auto_published: 'success',
    rejected: 'danger',
  }[review.status] as 'warning' | 'success' | 'danger';

  return (
    <>
      <div className="rounded-2xl bg-card border border-border p-5 space-y-4">
        {/* Header */}
        <div className="flex gap-3 items-start">
          <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center overflow-hidden shrink-0">
            {review.product_image ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={review.product_image} alt="" className="w-full h-full object-contain p-1" />
            ) : (
              <Package className="w-5 h-5 text-gray-400" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-sm line-clamp-1">{review.product_name}</p>
            {review.product_sku && <p className="text-xs text-muted">SKU: {review.product_sku}</p>}
          </div>
          <Badge variant={statusColor}>
            {review.status === 'auto_published' ? '⚡ Auto' :
             review.status === 'approved' ? '✅ Aprobada' :
             review.status === 'rejected' ? '❌ Rechazada' : '⏳ Pendiente'}
          </Badge>
        </div>

        {/* Rating + texto */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Stars rating={review.rating} />
            {review.title && <p className="font-semibold text-sm">"{review.title}"</p>}
          </div>
          {review.comment && (
            <p className="text-sm text-gray-700 italic">"{review.comment}"</p>
          )}
          {review.pet_name && (
            <p className="text-xs text-muted mt-1">Mascota: {review.pet_name}</p>
          )}
        </div>

        {/* Fotos */}
        {review.photo_urls.length > 0 && (
          <div className="flex gap-2">
            {review.photo_urls.map((url, i) => (
              <a key={i} href={url} target="_blank" rel="noopener noreferrer">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={url} alt="" className="w-16 h-16 rounded-xl object-cover border border-border hover:opacity-80 transition-opacity" />
              </a>
            ))}
          </div>
        )}

        {/* Cliente */}
        <div className="flex items-center gap-2 p-3 rounded-xl bg-gray-50 border">
          <User className="w-4 h-4 text-muted shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold">{review.customer_name}</p>
            {review.customer_phone && (
              <a href={`https://wa.me/57${review.customer_phone}`} className="text-xs text-brand-600 flex items-center gap-1 hover:underline">
                WhatsApp {review.customer_phone}
              </a>
            )}
          </div>
          {review.is_verified_purchase && (
            <Badge variant="success" className="text-xs">✓ Compra verificada</Badge>
          )}
        </div>

        {/* Respuesta admin */}
        {review.admin_reply && (
          <div className="p-3 rounded-xl bg-brand-50 border border-brand-100 text-sm text-brand-800">
            <p className="font-semibold text-xs text-brand-600 mb-1">Tu respuesta pública:</p>
            {review.admin_reply}
          </div>
        )}

        {/* Acciones */}
        {review.status === 'pending' && (
          <div className="flex gap-2">
            <Button
              className="flex-1"
              onClick={() => onModerate(review.id, 'approve')}
            >
              <CheckCircle className="w-4 h-4" /> Aprobar
            </Button>
            <Button
              variant="outline"
              className="flex-1 border-red-200 text-red-600 hover:bg-red-50"
              onClick={() => onModerate(review.id, 'reject', 'No cumple políticas')}
            >
              <XCircle className="w-4 h-4" /> Rechazar
            </Button>
            <Button variant="outline" onClick={() => setShowReply(true)}>
              <MessageSquare className="w-4 h-4" />
            </Button>
          </div>
        )}
        {review.status !== 'pending' && (
          <Button variant="outline" size="sm" onClick={() => setShowReply(true)}>
            <MessageSquare className="w-4 h-4" />
            {review.admin_reply ? 'Editar respuesta' : 'Responder'}
          </Button>
        )}
      </div>

      {showReply && <ReplyModal review={review} onClose={() => setShowReply(false)} />}
    </>
  );
}

// ── Página principal ──────────────────────────────────────────────────────────

const TABS = [
  { key: 'pending', label: 'Pendientes' },
  { key: 'approved', label: 'Aprobadas' },
  { key: 'auto_published', label: 'Auto-publicadas' },
  { key: 'rejected', label: 'Rechazadas' },
  { key: 'all', label: 'Todas' },
];

export default function ReviewsPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState('pending');
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ['admin-reviews', tab, page],
    queryFn: () => api<{ reviews: ReviewItem[]; total: number }>(`/admin/reviews?status_filter=${tab}&page=${page}&page_size=20`),
  });

  const { data: unmatched } = useQuery({
    queryKey: ['gbp-unmatched'],
    queryFn: () => api<Array<{ id: string; reviewer_name: string; rating: number; comment: string }>>('/admin/gbp-reviews/unmatched'),
  });

  const moderateMut = useMutation({
    mutationFn: ({ id, action, notes }: { id: string; action: 'approve' | 'reject'; notes?: string }) =>
      api(`/admin/reviews/${id}`, { method: 'PATCH', body: JSON.stringify({ action, notes }) }),
    onSuccess: (_, vars) => {
      toast.success(vars.action === 'approve' ? '✅ Reseña aprobada + puntos acreditados' : '❌ Reseña rechazada');
      qc.invalidateQueries({ queryKey: ['admin-reviews'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const syncMut = useMutation({
    mutationFn: () => api('/admin/gbp-sync/run', { method: 'POST' }),
    onSuccess: () => { toast.success('Sync GBP completado'); qc.invalidateQueries({ queryKey: ['gbp-unmatched'] }); },
    onError: (e: Error) => toast.error(e.message),
  });

  const reviews = data?.reviews ?? [];
  const total = data?.total ?? 0;
  const pendingCount = tab === 'pending' ? total : undefined;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <Star className="w-6 h-6 text-amber-400 fill-amber-400" /> Reseñas de Productos
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Modera reseñas · Responde a clientes · Sincroniza Google
          </p>
        </div>
        <Button variant="outline" onClick={() => syncMut.mutate()} disabled={syncMut.isPending}>
          <RefreshCw className={`w-4 h-4 ${syncMut.isPending ? 'animate-spin' : ''}`} />
          Sync GBP
        </Button>
      </div>

      {/* GBP unmatched alert */}
      {unmatched && unmatched.length > 0 && (
        <div className="rounded-2xl bg-amber-50 border border-amber-200 p-4">
          <p className="text-amber-800 font-semibold text-sm">
            ⚠️ {unmatched.length} reseña(s) de Google sin asignar a cliente
          </p>
          <p className="text-amber-700 text-xs mt-1">
            Asígnalas manualmente para acreditar 50 puntos a cada cliente.
          </p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); setPage(1); }}
            className={`px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-colors ${
              tab === t.key
                ? 'bg-brand-600 text-white'
                : 'bg-card border border-border hover:bg-accent text-muted-foreground'
            }`}
          >
            {t.label}
            {t.key === 'pending' && pendingCount ? ` (${pendingCount})` : ''}
          </button>
        ))}
      </div>

      {/* Reviews list */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-64 rounded-2xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : reviews.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Star className="w-12 h-12 mx-auto mb-3 text-gray-200" />
          <p className="font-medium">No hay reseñas en esta categoría</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {reviews.map((rev) => (
            <ReviewCard
              key={rev.id}
              review={rev}
              onModerate={(id, action, notes) => moderateMut.mutate({ id, action, notes })}
            />
          ))}
        </div>
      )}

      {/* Paginación */}
      {total > 20 && (
        <div className="flex justify-center gap-2">
          <Button variant="outline" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Anterior</Button>
          <span className="flex items-center px-4 text-sm text-muted">
            Pág {page} · {total} reseñas
          </span>
          <Button variant="outline" disabled={page * 20 >= total} onClick={() => setPage(p => p + 1)}>Siguiente</Button>
        </div>
      )}
    </div>
  );
}
