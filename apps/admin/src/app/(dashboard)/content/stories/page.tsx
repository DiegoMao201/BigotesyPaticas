'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Film, CheckCircle2, XCircle, RefreshCw, Play, Clock,
  Instagram, AlertTriangle, Wand2, ToggleLeft, ToggleRight,
  Eye, Calendar,
} from 'lucide-react';
import { toast } from 'sonner';
import { stories, type StoryItem } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusBadge(status: StoryItem['status']) {
  const map: Record<string, { label: string; className: string }> = {
    pending_approval: { label: 'Pendiente', className: 'bg-amber-100 text-amber-800 border-amber-200' },
    approved:         { label: 'Aprobado',  className: 'bg-blue-100 text-blue-800 border-blue-200' },
    scheduled:        { label: 'Programado',className: 'bg-blue-100 text-blue-800 border-blue-200' },
    published:        { label: 'Publicado', className: 'bg-green-100 text-green-800 border-green-200' },
    rejected:         { label: 'Rechazado', className: 'bg-red-100 text-red-800 border-red-200' },
    failed:           { label: 'Error',     className: 'bg-red-100 text-red-800 border-red-200' },
  };
  const s = map[status] ?? { label: status, className: 'bg-gray-100 text-gray-700' };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${s.className}`}>
      {s.label}
    </span>
  );
}

function fmtDate(iso: string) {
  try {
    return formatDistanceToNow(new Date(iso), { addSuffix: true, locale: es });
  } catch {
    return iso.slice(0, 10);
  }
}

// ── Video preview card ────────────────────────────────────────────────────────

function StoryCard({
  story,
  onApprove,
  onReject,
  loading,
}: {
  story: StoryItem;
  onApprove: () => void;
  onReject: () => void;
  loading: boolean;
}) {
  const [playing, setPlaying] = useState(false);

  return (
    <Card className="overflow-hidden border border-border">
      {/* Video / imagen */}
      <div className="relative bg-black aspect-[9/16] max-h-64 flex items-center justify-center overflow-hidden">
        {story.video_url ? (
          playing ? (
            <video
              src={story.video_url}
              autoPlay
              controls
              className="w-full h-full object-contain"
              onEnded={() => setPlaying(false)}
            />
          ) : (
            <>
              {story.base_image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={story.base_image_url}
                  alt="Story preview"
                  className="w-full h-full object-cover opacity-70"
                />
              ) : (
                <Film className="h-12 w-12 text-white/30" />
              )}
              <button
                onClick={() => setPlaying(true)}
                className="absolute inset-0 flex items-center justify-center group"
              >
                <div className="w-14 h-14 rounded-full bg-white/20 backdrop-blur flex items-center justify-center group-hover:bg-white/30 transition-colors">
                  <Play className="h-6 w-6 text-white ml-1" />
                </div>
              </button>
            </>
          )
        ) : story.base_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={story.base_image_url} alt="Story" className="w-full h-full object-cover" />
        ) : (
          <div className="flex flex-col items-center gap-2 text-white/40">
            <Film className="h-10 w-10" />
            <span className="text-xs">Sin video aún</span>
          </div>
        )}

        {/* Status badge overlay */}
        <div className="absolute top-2 left-2">
          {statusBadge(story.status)}
        </div>

        {/* Dry run badge */}
        {story.dry_run && (
          <div className="absolute top-2 right-2">
            <span className="text-[10px] bg-purple-600 text-white px-1.5 py-0.5 rounded font-medium">
              DRY RUN
            </span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-semibold text-foreground">
              {story.template_name ?? story.template_code ?? 'Story IA'}
            </p>
            <p className="text-[10px] text-muted-foreground capitalize">
              {story.template_category ?? 'general'}
            </p>
          </div>
          <div className="flex items-center gap-1 text-muted-foreground shrink-0">
            <Calendar className="h-3 w-3" />
            <span className="text-[10px]">{fmtDate(story.scheduled_at)}</span>
          </div>
        </div>

        {story.caption && (
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {story.caption}
          </p>
        )}

        {story.swipe_up_url && (
          <div className="flex items-center gap-1 text-[10px] text-brand-600">
            <Instagram className="h-3 w-3" />
            <span className="truncate">{story.swipe_up_url}</span>
          </div>
        )}

        {story.error_message && (
          <div className="flex items-start gap-1 p-1.5 rounded bg-red-50 border border-red-100">
            <AlertTriangle className="h-3 w-3 text-red-500 mt-0.5 shrink-0" />
            <p className="text-[10px] text-red-700 leading-tight">{story.error_message}</p>
          </div>
        )}

        {/* Actions */}
        {story.status === 'pending_approval' && (
          <div className="flex gap-2 pt-1">
            <Button
              size="sm"
              className="flex-1 h-8 text-xs bg-green-600 hover:bg-green-700 text-white"
              onClick={onApprove}
              disabled={loading}
            >
              <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
              Aprobar
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="flex-1 h-8 text-xs border-red-200 text-red-600 hover:bg-red-50"
              onClick={onReject}
              disabled={loading}
            >
              <XCircle className="h-3.5 w-3.5 mr-1" />
              Rechazar
            </Button>
          </div>
        )}

        {story.status === 'approved' && (
          <div className="flex items-center gap-1.5 text-[10px] text-blue-600 pt-1">
            <Clock className="h-3 w-3" />
            Programado para publicar automáticamente
          </div>
        )}

        {story.status === 'published' && (
          <div className="flex items-center gap-1.5 text-[10px] text-green-600 pt-1">
            <CheckCircle2 className="h-3 w-3" />
            Publicado {story.published_at ? fmtDate(story.published_at) : ''}
          </div>
        )}
      </div>
    </Card>
  );
}

// ── Config toggles ────────────────────────────────────────────────────────────

function ConfigPanel() {
  const qc = useQueryClient();
  const { data: cfg, isLoading } = useQuery({
    queryKey: ['stories-config'],
    queryFn: () => stories.getConfig(),
  });

  const updateMut = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      stories.updateConfig(key, value),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['stories-config'] });
      toast.success('Configuración actualizada');
    },
    onError: () => toast.error('Error al actualizar'),
  });

  if (isLoading || !cfg) return null;

  const isActive  = cfg.stories_active?.value === 'true';
  const isDryRun  = cfg.stories_dry_run_mode?.value === 'true';
  const perDay    = cfg.stories_per_day?.value ?? '1';

  return (
    <div className="flex flex-wrap gap-3 p-3 rounded-xl bg-muted/40 border border-border">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">Motor:</span>
        <button
          onClick={() => updateMut.mutate({ key: 'stories_active', value: isActive ? 'false' : 'true' })}
          className="flex items-center gap-1.5 text-xs font-semibold"
          disabled={updateMut.isPending}
        >
          {isActive
            ? <ToggleRight className="h-5 w-5 text-green-500" />
            : <ToggleLeft className="h-5 w-5 text-gray-400" />}
          <span className={isActive ? 'text-green-600' : 'text-muted-foreground'}>
            {isActive ? 'Activo' : 'Pausado'}
          </span>
        </button>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">Modo:</span>
        <button
          onClick={() => updateMut.mutate({ key: 'stories_dry_run_mode', value: isDryRun ? 'false' : 'true' })}
          className="flex items-center gap-1.5 text-xs font-semibold"
          disabled={updateMut.isPending}
        >
          {isDryRun
            ? <ToggleRight className="h-5 w-5 text-purple-500" />
            : <ToggleLeft className="h-5 w-5 text-gray-400" />}
          <span className={isDryRun ? 'text-purple-600' : 'text-muted-foreground'}>
            {isDryRun ? 'Dry Run (no publica)' : 'Publicación real'}
          </span>
        </button>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">Stories/día:</span>
        <select
          value={perDay}
          onChange={(e) => updateMut.mutate({ key: 'stories_per_day', value: e.target.value })}
          className="text-xs border border-border rounded px-1.5 py-0.5 bg-background"
          disabled={updateMut.isPending}
        >
          {['1','2','3'].map(v => <option key={v} value={v}>{v}</option>)}
        </select>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

type TabType = 'pending' | 'approved' | 'published' | 'all';

export default function StoriesPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<TabType>('pending');
  const [actionId, setActionId] = useState<string | null>(null);

  const statusFilter = tab === 'all' ? undefined : tab === 'approved' ? 'approved' : tab;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['stories', tab],
    queryFn: () => stories.list(statusFilter),
    refetchInterval: 30_000,
  });

  const updateMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'approved' | 'rejected' }) =>
      stories.updateStatus(id, status),
    onMutate: ({ id }) => setActionId(id),
    onSuccess: (_, { status }) => {
      toast.success(status === 'approved' ? '✅ Story aprobado' : '❌ Story rechazado');
      qc.invalidateQueries({ queryKey: ['stories'] });
    },
    onError: () => toast.error('Error al actualizar el story'),
    onSettled: () => setActionId(null),
  });

  const generateMut = useMutation({
    mutationFn: () => stories.generate(),
    onSuccess: (d) => {
      toast.success(`${d.queued} stories en cola para generar`);
      setTimeout(() => qc.invalidateQueries({ queryKey: ['stories'] }), 3000);
    },
    onError: () => toast.error('Error al generar stories'),
  });

  const items = data?.stories ?? [];
  const pendingCount = items.filter(s => s.status === 'pending_approval').length;

  const TABS: { key: TabType; label: string }[] = [
    { key: 'pending',   label: `Pendientes${pendingCount > 0 ? ` (${pendingCount})` : ''}` },
    { key: 'approved',  label: 'Aprobados' },
    { key: 'published', label: 'Publicados' },
    { key: 'all',       label: 'Todos' },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-display font-bold flex items-center gap-2">
            <Film className="h-6 w-6 text-brand-600" />
            Stories IA
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Revisa y aprueba los stories generados automáticamente antes de publicarlos
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-1.5 ${isLoading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
          <Button
            size="sm"
            className="gradient-brand text-white"
            onClick={() => generateMut.mutate()}
            disabled={generateMut.isPending}
          >
            <Wand2 className="h-4 w-4 mr-1.5" />
            {generateMut.isPending ? 'Generando...' : 'Generar ahora'}
          </Button>
        </div>
      </div>

      {/* Config panel */}
      <ConfigPanel />

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
              tab === t.key
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            } ${t.key === 'pending' && pendingCount > 0 ? 'text-amber-600 font-semibold' : ''}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-muted-foreground gap-2">
          <RefreshCw className="h-5 w-5 animate-spin" />
          Cargando stories...
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
          <Film className="h-12 w-12 text-muted-foreground/30" />
          <div>
            <p className="font-semibold text-foreground">
              {tab === 'pending' ? 'No hay stories pendientes de aprobación' : 'Sin stories en esta sección'}
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              {tab === 'pending'
                ? 'Haz clic en "Generar ahora" para crear nuevos stories'
                : 'Los stories aparecerán aquí cuando sean generados'}
            </p>
          </div>
          {tab === 'pending' && (
            <Button
              className="gradient-brand text-white"
              onClick={() => generateMut.mutate()}
              disabled={generateMut.isPending}
            >
              <Wand2 className="h-4 w-4 mr-1.5" />
              Generar stories ahora
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {items.map(story => (
            <StoryCard
              key={story.id}
              story={story}
              loading={actionId === story.id}
              onApprove={() => updateMut.mutate({ id: story.id, status: 'approved' })}
              onReject={() => updateMut.mutate({ id: story.id, status: 'rejected' })}
            />
          ))}
        </div>
      )}
    </div>
  );
}
