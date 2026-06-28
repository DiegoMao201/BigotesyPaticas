'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CalendarDays, CheckCircle2, XCircle, RotateCcw, Save,
  Power, TestTube2, Wand2, ChevronDown, ChevronUp, X,
  AlertTriangle, Clock, Instagram, Facebook, FlipHorizontal2,
  Zap, DollarSign,
} from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';

// ─── Types ────────────────────────────────────────────────────────────────────

type PostStatus = 'draft' | 'pending_approval' | 'approved' | 'rejected' | 'scheduled' | 'publishing' | 'published' | 'failed';

interface ScheduledPost {
  id: string;
  template_id: string | null;
  category: string;
  visual_prompt: string;
  caption: string;
  hashtags: string[];
  cta_url: string | null;
  image_url: string | null;
  image_url_alternative: string | null;
  image_model: string | null;
  alternative_image_model: string | null;
  image_cost_usd: number | null;
  alternative_cost_usd: number | null;
  scheduled_at: string;
  optimal_time_slot: string | null;
  target_platforms: string[];
  status: PostStatus;
  approved_at: string | null;
  rejected_reason: string | null;
  edited_by_admin: boolean;
  published_at: string | null;
  instagram_post_id: string | null;
  facebook_post_id: string | null;
  publish_error: string | null;
  dry_run: boolean;
  source_data: Record<string, unknown> | null;
  created_at: string;
}

interface Template {
  id: string;
  code: string;
  name: string;
  category: string;
  visual_style: string;
  cta_type: string | null;
}

interface EngineConfig {
  [key: string]: { value: string; description: string };
}

// ─── Content API ──────────────────────────────────────────────────────────────

const content = {
  list: (status = 'all', page = 1) =>
    api<{ items: ScheduledPost[]; total: number; page: number }>
      (`/v1/admin/content/scheduled-posts?status=${status}&page=${page}&page_size=50`),

  approve: (id: string) =>
    api(`/v1/admin/content/scheduled-posts/${id}/approve`, { method: 'POST' }),

  reject: (id: string, reason?: string) =>
    api(`/v1/admin/content/scheduled-posts/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  edit: (id: string, data: Partial<Pick<ScheduledPost, 'caption' | 'hashtags' | 'scheduled_at' | 'target_platforms' | 'visual_prompt'>>) =>
    api(`/v1/admin/content/scheduled-posts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  regenerateImage: (id: string, prompt?: string) =>
    api<{ ok: boolean; image_url: string }>(
      `/v1/admin/content/scheduled-posts/${id}/regenerate-image`,
      { method: 'POST', body: JSON.stringify({ visual_prompt: prompt ?? null }) },
    ),

  regenerateWithModel: (id: string, image_model: 'flux-1.1-pro' | 'gpt-image-1') =>
    api<{ ok: boolean; image_url: string; model: string; cost_usd: number }>(
      `/v1/admin/content/scheduled-posts/${id}/regenerate-with-model`,
      { method: 'POST', body: JSON.stringify({ image_model }) },
    ),

  approveAll: () =>
    api<{ ok: boolean; approved: number }>('/v1/admin/content/approve-all-pending', { method: 'POST' }),

  getConfig: () => api<EngineConfig>('/v1/admin/content/engine-config'),

  setConfig: (key: string, value: string) =>
    api('/v1/admin/content/engine-config', {
      method: 'PATCH',
      body: JSON.stringify({ key, value }),
    }),

  getTemplates: () => api<Template[]>('/v1/admin/content/templates'),

  generate: (template_code: string, context: Record<string, unknown>, scheduled_at?: string) =>
    api<ScheduledPost>('/v1/admin/content/generate', {
      method: 'POST',
      body: JSON.stringify({ template_code, context, scheduled_at }),
    }),

  triggerWeekPlan: () =>
    api<{ ok: boolean; output: string }>('/v1/admin/content/generate-week-plan', { method: 'POST' }),

  costSummary: (period = 'month') =>
    api<{
      period: string;
      gpt_count: number; gpt_cost: number;
      flux_count: number; flux_cost: number;
      total_count: number; total_cost: number;
      projection_end_of_month: number;
      gpt_only_projection: number;
      savings_vs_gpt: number;
    }>(`/v1/admin/content/cost-summary?period=${period}`),

  testPublish: (post_id: string, target: 'instagram' | 'facebook') =>
    api('/v1/admin/content/test-publish', {
      method: 'POST',
      body: JSON.stringify({ post_id, target }),
    }),
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_COLOR: Record<PostStatus, string> = {
  draft:            'bg-muted text-muted-foreground',
  pending_approval: 'bg-amber-100 text-amber-800 border-amber-200',
  approved:         'bg-emerald-100 text-emerald-800 border-emerald-200',
  scheduled:        'bg-blue-100 text-blue-800 border-blue-200',
  publishing:       'bg-purple-100 text-purple-800 border-purple-200',
  published:        'bg-green-100 text-green-800 border-green-200',
  rejected:         'bg-gray-100 text-gray-500 border-gray-200',
  failed:           'bg-red-100 text-red-800 border-red-200',
};

const STATUS_LABEL: Record<PostStatus, string> = {
  draft:            'Borrador',
  pending_approval: 'Pendiente',
  approved:         'Aprobado',
  scheduled:        'Programado',
  publishing:       'Publicando…',
  published:        'Publicado',
  rejected:         'Rechazado',
  failed:           'Error',
};

const CAT_BADGE: Record<string, string> = {
  product:     'bg-teal-100 text-teal-800',
  educational: 'bg-blue-100 text-blue-800',
  review:      'bg-purple-100 text-purple-800',
  awareness:   'bg-orange-100 text-orange-800',
  reminder:    'bg-yellow-100 text-yellow-800',
  meme:        'bg-pink-100 text-pink-800',
  local:       'bg-green-100 text-green-800',
};

// ─── Cost Widget ──────────────────────────────────────────────────────────────

function CostWidget() {
  const [open, setOpen] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ['cost-summary'],
    queryFn: () => content.costSummary('month'),
    refetchInterval: 120_000,
  });

  if (isLoading || !data) {
    return (
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-border bg-muted/50 text-muted-foreground"
      >
        <DollarSign className="w-3.5 h-3.5" /> Costos IA…
      </button>
    );
  }

  const hasMix = data.flux_count > 0 && data.gpt_count > 0;
  const totalLabel = `$${data.total_cost.toFixed(2)} USD`;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-colors ${
          hasMix
            ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
            : 'border-amber-200 bg-amber-50 text-amber-700'
        }`}
      >
        <DollarSign className="w-3.5 h-3.5" />
        <span className="font-medium">Costos IA:</span>
        <span className="font-mono">{totalLabel}</span>
        {hasMix && <span className="text-emerald-500 font-medium">↓${data.savings_vs_gpt.toFixed(0)} ahorrado</span>}
        {open ? <ChevronUp className="w-3 h-3 ml-1" /> : <ChevronDown className="w-3 h-3 ml-1" />}
      </button>

      {open && (
        <div className="absolute top-full right-0 mt-1 w-72 bg-background border border-border rounded-xl shadow-lg p-4 z-30 text-xs">
          <div className="font-semibold mb-2 text-sm">💰 Costo IA — {new Date().toLocaleString('es-CO', { month: 'long', year: 'numeric' })}</div>
          <div className="space-y-1.5">
            {data.gpt_count > 0 && (
              <div className="flex justify-between items-center">
                <span className="text-amber-700">GPT-image-1 ({data.gpt_count} imgs)</span>
                <span className="font-mono text-amber-600">${data.gpt_cost.toFixed(2)}</span>
              </div>
            )}
            {data.flux_count > 0 && (
              <div className="flex justify-between items-center">
                <span className="text-emerald-700">Flux 1.1 Pro ({data.flux_count} imgs)</span>
                <span className="font-mono text-emerald-600">${data.flux_cost.toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between items-center border-t pt-1.5 font-medium">
              <span>Total este mes</span>
              <span className="font-mono">${data.total_cost.toFixed(2)}</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t space-y-1 text-muted-foreground">
            <div className="flex justify-between">
              <span>Proyección fin de mes</span>
              <span className="font-mono text-foreground">${data.projection_end_of_month}</span>
            </div>
            <div className="flex justify-between">
              <span>Si fuera 100% GPT</span>
              <span className="font-mono text-amber-600">${data.gpt_only_projection}</span>
            </div>
            {data.savings_vs_gpt > 0 && (
              <div className="flex justify-between text-emerald-600 font-medium">
                <span>Ahorro mix inteligente</span>
                <span className="font-mono">${data.savings_vs_gpt.toFixed(2)}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── AB Test Modal ────────────────────────────────────────────────────────────

function AbTestModal({
  posts,
  config,
  onClose,
  onModelChanged,
}: {
  posts: ScheduledPost[];
  config: EngineConfig;
  onClose: () => void;
  onModelChanged: () => void;
}) {
  const qc = useQueryClient();
  const [generatingId, setGeneratingId] = useState<string | null>(null);

  const currentModel = config['default_image_model']?.value ?? 'gpt-image-1';

  const setModelMut = useMutation({
    mutationFn: (model: string) => content.setConfig('default_image_model', model),
    onSuccess: (_, model) => {
      toast.success(`✅ Modelo cambiado a ${model}`);
      qc.invalidateQueries({ queryKey: ['engine-config'] });
      onModelChanged();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  async function generateFlux(post: ScheduledPost) {
    setGeneratingId(post.id);
    try {
      const res = await content.regenerateWithModel(post.id, 'flux-1.1-pro');
      toast.success(`✅ Imagen Flux generada — $${res.cost_usd.toFixed(2)}`);
      qc.invalidateQueries({ queryKey: ['content-posts'] });
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error generando imagen');
    } finally {
      setGeneratingId(null);
    }
  }

  // Calcular totales
  const gptTotal = posts.reduce((s, p) => s + (p.image_cost_usd ?? 0.50), 0);
  const fluxTotal = posts.reduce((s, p) => s + (p.alternative_cost_usd ?? 0), 0);
  const postsWithAlt = posts.filter((p) => p.image_url_alternative).length;
  const MONTHLY_POSTS = 90;
  const gptMonthly = MONTHLY_POSTS * 0.50;
  const fluxMonthly = MONTHLY_POSTS * 0.04;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <button className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-background rounded-2xl shadow-2xl w-full max-w-5xl mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-background/95 backdrop-blur border-b border-border px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="font-bold text-lg flex items-center gap-2">
              <FlipHorizontal2 className="w-5 h-5 text-brand-600" />
              Comparación A/B — GPT-image-1 vs Flux 1.1 Pro
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {postsWithAlt}/{posts.length} imágenes Flux generadas ·
              Modelo actual: <span className="font-medium">{currentModel}</span>
            </p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Comparación por post */}
          {posts.map((post) => (
            <Card key={post.id} className="p-4">
              <div className="flex items-center justify-between mb-3">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded uppercase ${CAT_BADGE[post.category] || 'bg-muted'}`}>
                  {post.category}
                </span>
                <span className="text-xs text-muted-foreground line-clamp-1 flex-1 mx-3">{post.caption.slice(0, 80)}…</span>
                {!post.image_url_alternative && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => generateFlux(post)}
                    disabled={generatingId === post.id}
                    className="shrink-0 text-xs"
                  >
                    <Zap className="w-3 h-3 mr-1" />
                    {generatingId === post.id ? 'Generando…' : 'Generar con Flux'}
                  </Button>
                )}
              </div>
              <div className="grid grid-cols-2 gap-4">
                {/* GPT image */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-medium text-muted-foreground">GPT-image-1</span>
                    <span className="text-xs text-amber-600 font-mono">$0.50</span>
                  </div>
                  {post.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={post.image_url} alt="GPT" className="w-full aspect-square object-cover rounded-lg border border-border" />
                  ) : (
                    <div className="w-full aspect-square bg-muted rounded-lg flex items-center justify-center text-xs text-muted-foreground">
                      Sin imagen
                    </div>
                  )}
                </div>
                {/* Flux image */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-medium text-muted-foreground">Flux 1.1 Pro</span>
                    <span className="text-xs text-emerald-600 font-mono">$0.04</span>
                  </div>
                  {post.image_url_alternative ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={post.image_url_alternative} alt="Flux" className="w-full aspect-square object-cover rounded-lg border border-border" />
                  ) : (
                    <div className="w-full aspect-square bg-muted/50 rounded-lg flex flex-col items-center justify-center text-xs text-muted-foreground border border-dashed border-border">
                      <Zap className="w-5 h-5 mb-1 opacity-30" />
                      {generatingId === post.id ? 'Generando…' : 'Pendiente'}
                    </div>
                  )}
                </div>
              </div>
            </Card>
          ))}

          {/* Resumen de costos */}
          <Card className="p-5 bg-gradient-to-br from-slate-50 to-slate-100/50 border-slate-200">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-brand-600" />
              Análisis de costos
            </h3>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <div className="text-xs text-muted-foreground mb-1">Test actual ({posts.length} imágenes)</div>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>GPT-image-1</span>
                    <span className="font-mono text-amber-600">${gptTotal.toFixed(2)}</span>
                  </div>
                  {postsWithAlt > 0 && (
                    <div className="flex justify-between text-sm">
                      <span>Flux 1.1 Pro ({postsWithAlt})</span>
                      <span className="font-mono text-emerald-600">${fluxTotal.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Proyección mensual ({MONTHLY_POSTS} posts)</div>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>GPT-image-1</span>
                    <span className="font-mono text-amber-600">${gptMonthly.toFixed(0)}/mes</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Flux 1.1 Pro</span>
                    <span className="font-mono text-emerald-600">${fluxMonthly.toFixed(2)}/mes</span>
                  </div>
                  <div className="flex justify-between text-sm font-semibold border-t pt-1 mt-1">
                    <span>Ahorro anual</span>
                    <span className="font-mono text-brand-600">${((gptMonthly - fluxMonthly) * 12).toFixed(0)}/año</span>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {/* Decisión */}
          <div className="space-y-3">
            <p className="text-sm font-medium text-center">¿Qué modelo usar a partir de ahora?</p>
            <div className="grid grid-cols-3 gap-3">
              <Button
                variant={currentModel === 'gpt-image-1' ? 'default' : 'outline'}
                onClick={() => setModelMut.mutate('gpt-image-1')}
                disabled={setModelMut.isPending}
                className={currentModel === 'gpt-image-1' ? 'gradient-brand text-white' : ''}
              >
                🤖 Mantener GPT-image-1
                <span className="block text-[10px] font-normal opacity-75 mt-0.5">$45/mes</span>
              </Button>
              <Button
                variant={currentModel === 'flux-1.1-pro' ? 'default' : 'outline'}
                onClick={() => setModelMut.mutate('flux-1.1-pro')}
                disabled={setModelMut.isPending}
                className={currentModel === 'flux-1.1-pro' ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'border-emerald-300 text-emerald-700 hover:bg-emerald-50'}
              >
                ⚡ Cambiar a Flux Pro
                <span className="block text-[10px] font-normal opacity-75 mt-0.5">$3.60/mes</span>
              </Button>
              <Button variant="outline" onClick={onClose}>
                🧐 Decidir más tarde
              </Button>
            </div>
            {currentModel !== 'gpt-image-1' && (
              <p className="text-xs text-center text-emerald-600">
                ✅ Configurado: próximas imágenes se generan con {currentModel}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Components ───────────────────────────────────────────────────────────────

function EngineControls({ config, onToggle }: { config: EngineConfig; onToggle: (key: string, val: string) => void }) {
  const isActive  = config['is_active']?.value === 'true';
  const isDryRun  = config['dry_run_mode']?.value === 'true';
  return (
    <div className="flex items-center gap-3 flex-wrap">
      <button
        onClick={() => onToggle('is_active', isActive ? 'false' : 'true')}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
          isActive ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-muted border-border text-muted-foreground'
        }`}
      >
        <Power className="w-3.5 h-3.5" />
        {isActive ? '✅ Engine activo' : '⏸ Engine pausado'}
      </button>
      <button
        onClick={() => onToggle('dry_run_mode', isDryRun ? 'false' : 'true')}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
          isDryRun ? 'bg-blue-50 border-blue-200 text-blue-700' : 'bg-amber-50 border-amber-200 text-amber-700'
        }`}
      >
        <TestTube2 className="w-3.5 h-3.5" />
        {isDryRun ? '🧪 Dry-run ON' : '🚀 Publicación real'}
      </button>
    </div>
  );
}

function PostCard({ post, onClick }: { post: ScheduledPost; onClick: () => void }) {
  const dt = new Date(post.scheduled_at);
  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-xl border-2 p-3 transition-all hover:shadow-md ${STATUS_COLOR[post.status]} cursor-pointer`}
    >
      {post.image_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={post.image_url} alt="" className="w-full aspect-square object-cover rounded-lg mb-2" />
      )}
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase ${CAT_BADGE[post.category] || 'bg-muted text-muted-foreground'}`}>
          {post.category}
        </span>
        <span className="text-[10px] text-muted-foreground whitespace-nowrap">
          {dt.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      <p className="text-xs line-clamp-2 mt-1 text-current/80">{post.caption}</p>
      <div className="mt-1.5 flex items-center gap-1 flex-wrap">
        <Badge className={`text-[10px] border ${STATUS_COLOR[post.status]}`}>
          {STATUS_LABEL[post.status]}
        </Badge>
        {post.image_url_alternative && (
          <span className="text-[10px] text-emerald-600">⚡ A/B</span>
        )}
      </div>
    </button>
  );
}

function PostDrawer({
  post,
  onClose,
  onUpdate,
}: {
  post: ScheduledPost;
  onClose: () => void;
  onUpdate: () => void;
}) {
  const qc = useQueryClient();
  const [caption, setCaption] = useState(post.caption);
  const [hashtags, setHashtags] = useState((post.hashtags || []).join(' '));
  const [showPrompt, setShowPrompt] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [showReject, setShowReject] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');
  const [showRegenPrompt, setShowRegenPrompt] = useState(false);

  const saveMut = useMutation({
    mutationFn: () => content.edit(post.id, {
      caption,
      hashtags: hashtags.split(/\s+/).filter(Boolean),
    }),
    onSuccess: () => { toast.success('Cambios guardados'); onUpdate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const approveMut = useMutation({
    mutationFn: () => content.approve(post.id),
    onSuccess: () => { toast.success('✅ Post aprobado'); onUpdate(); onClose(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const rejectMut = useMutation({
    mutationFn: () => content.reject(post.id, rejectReason || undefined),
    onSuccess: () => { toast.success('Post rechazado'); onUpdate(); onClose(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const regenMut = useMutation({
    mutationFn: () => content.regenerateImage(post.id, customPrompt || undefined),
    onSuccess: () => { toast.success('Nueva imagen generada'); onUpdate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const altModel = post.image_model === 'flux-1.1-pro' ? 'gpt-image-1' : 'flux-1.1-pro';
  const regenWithModelMut = useMutation({
    mutationFn: () => content.regenerateWithModel(post.id, altModel),
    onSuccess: (res) => {
      toast.success(`✅ Imagen regenerada con ${res.model} — $${res.cost_usd.toFixed(2)}`);
      onUpdate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button className="absolute inset-0 bg-black/40" onClick={onClose} aria-label="Cerrar" />
      <div className="relative w-full max-w-xl bg-background shadow-2xl overflow-y-auto flex flex-col">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-background/95 backdrop-blur border-b border-border px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-semibold px-2 py-0.5 rounded uppercase ${CAT_BADGE[post.category] || 'bg-muted'}`}>
              {post.category}
            </span>
            <Badge className={`text-xs border ${STATUS_COLOR[post.status]}`}>
              {STATUS_LABEL[post.status]}
            </Badge>
            {post.dry_run && <Badge className="text-xs bg-blue-100 text-blue-700 border-blue-200">dry-run</Badge>}
          </div>
          <button onClick={onClose} className="rounded-md p-1.5 hover:bg-muted">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-5 flex-1">
          {/* Imagen */}
          {post.image_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={post.image_url} alt="" className="w-full aspect-square object-cover rounded-xl border border-border" />
          )}

          {/* Imagen alternativa (Flux) si existe */}
          {post.image_url_alternative && (
            <div>
              <p className="text-[10px] text-muted-foreground mb-1 flex items-center gap-1">
                <Zap className="w-3 h-3 text-emerald-500" />
                Alternativa Flux 1.1 Pro (${(post.alternative_cost_usd ?? 0.04).toFixed(2)})
              </p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={post.image_url_alternative} alt="Flux alt" className="w-full aspect-square object-cover rounded-xl border border-emerald-200" />
            </div>
          )}

          {/* Modelo IA + costo + botón regenerar con alternativo */}
          {post.image_model && (
            <div className="flex items-center justify-between gap-2 flex-wrap">
              {post.image_model === 'flux-1.1-pro' ? (
                <span className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700">
                  <Zap className="w-3 h-3" /> Flux 1.1 Pro
                  <span className="font-mono bg-emerald-100 px-1 rounded text-emerald-600">$0.04</span>
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-700">
                  💰 GPT-image-1 (high)
                  <span className="font-mono bg-amber-100 px-1 rounded">$0.50</span>
                </span>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => regenWithModelMut.mutate()}
                disabled={regenWithModelMut.isPending}
                className="text-xs h-7 px-2"
              >
                <RotateCcw className="w-3 h-3 mr-1" />
                {regenWithModelMut.isPending
                  ? 'Generando…'
                  : `Regenerar con ${altModel === 'flux-1.1-pro' ? 'Flux' : 'GPT'}`}
              </Button>
            </div>
          )}

          {/* Programación */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="w-4 h-4" />
            <span>{new Date(post.scheduled_at).toLocaleString('es-CO', { dateStyle: 'full', timeStyle: 'short' })}</span>
          </div>

          {/* Plataformas */}
          <div className="flex gap-2">
            {(post.target_platforms || []).includes('instagram') && (
              <span className="flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-pink-50 border border-pink-200 text-pink-700">
                <Instagram className="w-3 h-3" /> Instagram
              </span>
            )}
            {(post.target_platforms || []).includes('facebook') && (
              <span className="flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700">
                <Facebook className="w-3 h-3" /> Facebook
              </span>
            )}
          </div>

          {/* Visual prompt (toggle) */}
          <div>
            <button
              onClick={() => setShowPrompt(!showPrompt)}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-1"
            >
              {showPrompt ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {showPrompt ? 'Ocultar' : 'Ver'} visual prompt
            </button>
            {showPrompt && (
              <p className="text-[11px] text-muted-foreground bg-muted/50 rounded-lg p-3 font-mono leading-relaxed">
                {post.visual_prompt}
              </p>
            )}
          </div>

          {/* Caption editable */}
          <div>
            <label className="text-xs font-medium block mb-1.5">Caption</label>
            <textarea
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              rows={8}
              className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring resize-none"
            />
          </div>

          {/* Hashtags */}
          <div>
            <label className="text-xs font-medium block mb-1.5">Hashtags</label>
            <input
              value={hashtags}
              onChange={(e) => setHashtags(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="#BigotesYPaticasPereira #MascotasPereira"
            />
          </div>

          {/* Source data */}
          {post.source_data && Object.keys(post.source_data).length > 0 && (
            <details className="text-xs">
              <summary className="cursor-pointer text-muted-foreground">Datos fuente del post</summary>
              <pre className="mt-1 p-2 bg-muted rounded text-[10px] overflow-x-auto">
                {JSON.stringify(post.source_data, null, 2)}
              </pre>
            </details>
          )}

          {/* Error */}
          {post.publish_error && (
            <div className="text-xs text-destructive bg-destructive/10 rounded-lg p-3">
              <AlertTriangle className="w-3 h-3 inline mr-1" />
              {post.publish_error}
            </div>
          )}

          {/* Published info */}
          {post.status === 'published' && (
            <div className="text-xs text-emerald-700 bg-emerald-50 rounded-lg p-3 space-y-0.5">
              <div>✅ Publicado {post.published_at ? formatDistanceToNow(new Date(post.published_at), { locale: es, addSuffix: true }) : ''}</div>
              {post.instagram_post_id && <div>IG: {post.instagram_post_id}</div>}
              {post.facebook_post_id && <div>FB: {post.facebook_post_id}</div>}
              {post.dry_run && <div className="text-blue-600">🧪 dry-run — no publicado en redes reales</div>}
            </div>
          )}
        </div>

        {/* Acciones sticky */}
        <div className="sticky bottom-0 bg-background/95 backdrop-blur border-t border-border p-4 space-y-2">
          {/* Regenerar imagen */}
          <div>
            <button
              onClick={() => setShowRegenPrompt(!showRegenPrompt)}
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 mb-1"
            >
              {showRegenPrompt ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              Prompt personalizado para regenerar
            </button>
            {showRegenPrompt && (
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                rows={3}
                placeholder="Dejar vacío para usar prompt original..."
                className="w-full px-3 py-2 text-xs rounded-lg border border-input bg-background focus:outline-none resize-none mb-1"
              />
            )}
          </div>

          <div className="flex gap-2 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={() => regenMut.mutate()}
              disabled={regenMut.isPending}
              className="flex-1"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              {regenMut.isPending ? 'Generando…' : 'Regenerar imagen'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => saveMut.mutate()}
              disabled={saveMut.isPending}
              className="flex-1"
            >
              <Save className="w-3.5 h-3.5" />
              {saveMut.isPending ? 'Guardando…' : 'Guardar'}
            </Button>
          </div>

          {post.status === 'pending_approval' && (
            <>
              <Button
                className="w-full gradient-brand text-white"
                onClick={() => approveMut.mutate()}
                disabled={approveMut.isPending}
              >
                <CheckCircle2 className="w-4 h-4" />
                {approveMut.isPending ? 'Aprobando…' : '✅ Aprobar para publicar'}
              </Button>

              {!showReject ? (
                <button
                  onClick={() => setShowReject(true)}
                  className="w-full text-sm text-muted-foreground hover:text-destructive text-center py-1"
                >
                  Rechazar post
                </button>
              ) : (
                <div className="space-y-1.5">
                  <input
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Motivo (opcional)"
                    className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none"
                  />
                  <Button
                    variant="outline"
                    className="w-full border-destructive text-destructive hover:bg-destructive/10"
                    onClick={() => rejectMut.mutate()}
                    disabled={rejectMut.isPending}
                  >
                    <XCircle className="w-4 h-4" />
                    {rejectMut.isPending ? 'Rechazando…' : '❌ Confirmar rechazo'}
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function GenerateModal({ templates, onClose, onGenerated }: {
  templates: Template[];
  onClose: () => void;
  onGenerated: () => void;
}) {
  const [templateCode, setTemplateCode] = useState('product_hero');
  const [contextJson, setContextJson] = useState('{\n  "product_name": "Royal Canin Adult 15kg",\n  "product_price": 185000,\n  "slug": "royal-canin-adult-15kg"\n}');
  const [scheduledAt, setScheduledAt] = useState('');
  const [error, setError] = useState('');

  const genMut = useMutation({
    mutationFn: () => {
      let ctx: Record<string, unknown>;
      try { ctx = JSON.parse(contextJson); } catch { throw new Error('Context JSON inválido'); }
      return content.generate(templateCode, ctx, scheduledAt || undefined);
    },
    onSuccess: () => { toast.success('Post generado y en cola de aprobación'); onGenerated(); onClose(); },
    onError: (e: Error) => { setError(e.message); toast.error(e.message); },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <button className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-background rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-lg flex items-center gap-2"><Wand2 className="w-5 h-5 text-brand-600" /> Generar post manual</h2>
          <button onClick={onClose}><X className="w-4 h-4" /></button>
        </div>

        <div>
          <label className="text-xs font-medium block mb-1">Template</label>
          <select
            value={templateCode}
            onChange={(e) => setTemplateCode(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none"
          >
            {templates.map((t) => (
              <option key={t.code} value={t.code}>{t.name} ({t.category})</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs font-medium block mb-1">Contexto (JSON)</label>
          <textarea
            value={contextJson}
            onChange={(e) => setContextJson(e.target.value)}
            rows={6}
            className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-input bg-background focus:outline-none resize-none"
          />
        </div>

        <div>
          <label className="text-xs font-medium block mb-1">Programar para (opcional)</label>
          <input
            type="datetime-local"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-input bg-background focus:outline-none"
          />
        </div>

        {error && <p className="text-xs text-destructive">{error}</p>}

        <Button
          className="w-full gradient-brand text-white"
          onClick={() => genMut.mutate()}
          disabled={genMut.isPending}
        >
          <Wand2 className="w-4 h-4" />
          {genMut.isPending ? 'Generando (puede tardar 30-60s)…' : 'Generar con IA'}
        </Button>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

type TabStatus = 'pending_approval' | 'approved' | 'published' | 'rejected' | 'all';

const TABS: { label: string; value: TabStatus }[] = [
  { label: 'Pendientes', value: 'pending_approval' },
  { label: 'Aprobados', value: 'approved' },
  { label: 'Publicados', value: 'published' },
  { label: 'Rechazados', value: 'rejected' },
  { label: 'Todos', value: 'all' },
];

export default function ContentCalendarPage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabStatus>('pending_approval');
  const [selectedPost, setSelectedPost] = useState<ScheduledPost | null>(null);
  const [showGenerate, setShowGenerate] = useState(false);
  const [showAbTest, setShowAbTest] = useState(false);
  const [triggeringPlan, setTriggeringPlan] = useState(false);

  const { data: postsData, isLoading } = useQuery({
    queryKey: ['content-posts', activeTab],
    queryFn: () => content.list(activeTab),
    refetchInterval: 30_000,
  });

  const { data: allPostsData } = useQuery({
    queryKey: ['content-posts', 'all'],
    queryFn: () => content.list('all'),
    enabled: showAbTest,
  });

  const { data: config } = useQuery({
    queryKey: ['engine-config'],
    queryFn: content.getConfig,
    refetchInterval: 60_000,
  });

  const { data: templates } = useQuery({
    queryKey: ['content-templates'],
    queryFn: content.getTemplates,
  });

  const configMut = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) => content.setConfig(key, value),
    onSuccess: () => { toast.success('Configuración actualizada'); qc.invalidateQueries({ queryKey: ['engine-config'] }); },
    onError: (e: Error) => toast.error(e.message),
  });

  const approveAllMut = useMutation({
    mutationFn: content.approveAll,
    onSuccess: (data) => {
      toast.success(`✅ ${data.approved} posts aprobados`);
      qc.invalidateQueries({ queryKey: ['content-posts'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  async function handleTriggerPlan() {
    setTriggeringPlan(true);
    try {
      const result = await content.triggerWeekPlan();
      if (result.ok) {
        toast.success('Plan semanal generado correctamente');
      } else {
        toast.error('Error generando plan semanal');
      }
      qc.invalidateQueries({ queryKey: ['content-posts'] });
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error desconocido');
    } finally {
      setTriggeringPlan(false);
    }
  }

  const posts = postsData?.items ?? [];
  const total  = postsData?.total ?? 0;
  const pendingCount = posts.filter((p) => p.status === 'pending_approval').length;
  const allPosts = allPostsData?.items ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <CalendarDays className="w-6 h-6 text-brand-600" /> Contenido IA
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {total} posts · {pendingCount} pendientes de aprobación
          </p>
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          <CostWidget />
          <Button
            variant="outline"
            onClick={() => setShowAbTest(true)}
            className="border-emerald-300 text-emerald-700 hover:bg-emerald-50"
          >
            <FlipHorizontal2 className="w-4 h-4" /> Comparar modelos IA
          </Button>
          <Button variant="outline" onClick={() => setShowGenerate(true)}>
            <Wand2 className="w-4 h-4" /> Generar post
          </Button>
          <Button
            variant="outline"
            onClick={handleTriggerPlan}
            disabled={triggeringPlan}
          >
            <CalendarDays className="w-4 h-4" />
            {triggeringPlan ? 'Generando plan…' : 'Plan semanal'}
          </Button>
          {pendingCount > 0 && (
            <Button
              onClick={() => {
                if (confirm(`¿Aprobar los ${pendingCount} posts pendientes?`)) {
                  approveAllMut.mutate();
                }
              }}
              disabled={approveAllMut.isPending}
              className="gradient-brand text-white"
            >
              <CheckCircle2 className="w-4 h-4" />
              Aprobar todos ({pendingCount})
            </Button>
          )}
        </div>
      </div>

      {/* Engine controls */}
      {config && (
        <Card className="p-4">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <span className="text-sm font-medium text-muted-foreground">Control del engine:</span>
            <EngineControls
              config={config}
              onToggle={(key, value) => configMut.mutate({ key, value })}
            />
          </div>
          {config['dry_run_mode']?.value === 'false' && config['is_active']?.value === 'true' && (
            <div className="mt-3 flex items-center gap-2 text-sm text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              ⚠️ Engine activo en modo PRODUCCIÓN — los posts aprobados se publicarán en Instagram y Facebook reales.
            </div>
          )}
        </Card>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border overflow-x-auto">
        {TABS.map((tab) => {
          const count = tab.value === 'all' ? total : undefined;
          return (
            <button
              key={tab.value}
              onClick={() => setActiveTab(tab.value)}
              className={`px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                activeTab === tab.value
                  ? 'border-brand-600 text-brand-700'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
              {tab.value === 'pending_approval' && pendingCount > 0 && (
                <span className="ml-1.5 bg-amber-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                  {pendingCount}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Posts grid */}
      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Cargando posts…</div>
      ) : posts.length === 0 ? (
        <Card className="p-12 text-center">
          <CalendarDays className="h-12 w-12 mx-auto text-muted-foreground mb-4 opacity-30" />
          <p className="text-muted-foreground">
            {activeTab === 'pending_approval'
              ? 'No hay posts pendientes de aprobación'
              : `Sin posts con estado "${activeTab}"`}
          </p>
          {activeTab === 'pending_approval' && (
            <Button className="mt-4" variant="outline" onClick={() => setShowGenerate(true)}>
              <Wand2 className="w-4 h-4" /> Generar primer post
            </Button>
          )}
        </Card>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
          {posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              onClick={() => setSelectedPost(post)}
            />
          ))}
        </div>
      )}

      {/* Drawer de detalle */}
      {selectedPost && (
        <PostDrawer
          post={selectedPost}
          onClose={() => setSelectedPost(null)}
          onUpdate={() => {
            qc.invalidateQueries({ queryKey: ['content-posts'] });
            content.list(activeTab).then((data) => {
              const updated = data.items.find((p) => p.id === selectedPost.id);
              if (updated) setSelectedPost(updated);
            });
          }}
        />
      )}

      {/* Modal generar */}
      {showGenerate && templates && (
        <GenerateModal
          templates={templates}
          onClose={() => setShowGenerate(false)}
          onGenerated={() => qc.invalidateQueries({ queryKey: ['content-posts'] })}
        />
      )}

      {/* Modal A/B test */}
      {showAbTest && config && (
        <AbTestModal
          posts={allPosts}
          config={config}
          onClose={() => setShowAbTest(false)}
          onModelChanged={() => qc.invalidateQueries({ queryKey: ['engine-config'] })}
        />
      )}
    </div>
  );
}
