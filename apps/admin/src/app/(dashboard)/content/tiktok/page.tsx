'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Music2, CheckCircle2, AlertTriangle, ExternalLink, Loader2, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { tiktok } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

export default function TikTokPage() {
  return (
    <Suspense fallback={<div className="text-sm text-muted-foreground">Cargando…</div>}>
      <TikTokPageInner />
    </Suspense>
  );
}

function TikTokPageInner() {
  const qc = useQueryClient();
  const router = useRouter();
  const params = useSearchParams();
  const [videoUrl, setVideoUrl] = useState('');
  const [caption, setCaption] = useState('');
  const [lastPublishId, setLastPublishId] = useState<string | null>(null);

  const { data: status, isLoading } = useQuery({
    queryKey: ['tiktok-status'],
    queryFn: () => tiktok.status(),
    refetchInterval: 30_000,
  });

  useEffect(() => {
    if (params.get('connected') === '1') {
      toast.success('¡Cuenta de TikTok conectada!');
      qc.invalidateQueries({ queryKey: ['tiktok-status'] });
      router.replace('/content/tiktok');
    }
    const err = params.get('error');
    if (err) {
      toast.error(`Error conectando TikTok: ${err}`);
      router.replace('/content/tiktok');
    }
  }, [params, qc, router]);

  const connectMut = useMutation({
    mutationFn: () => tiktok.authorize(),
    onSuccess: (data) => {
      window.location.href = data.authorize_url;
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const publishMut = useMutation({
    mutationFn: () => tiktok.testPublish(videoUrl, caption),
    onSuccess: (data) => {
      toast.success(`Enviado a TikTok (privacidad: ${data.privacy_level_used}). Revisa el estado abajo.`);
      setLastPublishId(data.publish_id);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const statusQuery = useQuery({
    queryKey: ['tiktok-publish-status', lastPublishId],
    queryFn: () => tiktok.publishStatus(lastPublishId!),
    enabled: !!lastPublishId,
    refetchInterval: (query) => (query.state.data?.status === 'PUBLISH_COMPLETE' ? false : 4000),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-display font-bold tracking-tight flex items-center gap-2">
          <Music2 className="h-7 w-7" /> TikTok
        </h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Content Posting API — mientras la app no esté auditada, las publicaciones quedan en modo privado (solo las ve la cuenta dueña).
        </p>
      </div>

      <Card className="p-5">
        {isLoading ? (
          <div className="text-sm text-muted-foreground">Cargando estado…</div>
        ) : status?.connected ? (
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-6 w-6 text-emerald-600" />
              <div>
                <p className="font-semibold">Cuenta conectada{status.username ? `: @${status.username}` : ''}</p>
                <p className="text-xs text-muted-foreground">
                  Token vence: {status.access_token_expires_at ? new Date(status.access_token_expires_at).toLocaleString('es-CO') : '—'}
                </p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={() => connectMut.mutate()} disabled={connectMut.isPending}>
              <RefreshCw className="h-4 w-4 mr-1" /> Reconectar / cambiar cuenta
            </Button>
          </div>
        ) : (
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-6 w-6 text-amber-500" />
              <p className="font-semibold">No hay ninguna cuenta de TikTok conectada</p>
            </div>
            <Button onClick={() => connectMut.mutate()} disabled={connectMut.isPending}>
              {connectMut.isPending ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <ExternalLink className="h-4 w-4 mr-1" />}
              Conectar cuenta de TikTok
            </Button>
          </div>
        )}
      </Card>

      {status?.connected && (
        <Card className="p-5 space-y-4">
          <h2 className="font-display font-semibold text-lg">Publicación de prueba (Sandbox)</h2>
          <p className="text-xs text-muted-foreground">
            Mientras la app esté en Sandbox/sin auditar, esto publica en privado (solo lo ves tú en la app de TikTok) —
            es para confirmar que la integración funciona antes de pedir la auditoría.
          </p>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium mb-1 block">URL del video (mp4, público)</label>
              <Input value={videoUrl} onChange={(e) => setVideoUrl(e.target.value)} placeholder="https://.../video.mp4" />
            </div>
            <div>
              <label className="text-xs font-medium mb-1 block">Caption</label>
              <Input value={caption} onChange={(e) => setCaption(e.target.value)} placeholder="Texto del video…" />
            </div>
            <Button onClick={() => publishMut.mutate()} disabled={!videoUrl || publishMut.isPending}>
              {publishMut.isPending ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : null}
              Publicar de prueba
            </Button>
          </div>

          {lastPublishId && (
            <div className="rounded-xl border border-border p-4 space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold">Estado de la publicación</p>
                <Badge className="bg-blue-100 text-blue-700">{String(statusQuery.data?.status ?? '...')}</Badge>
              </div>
              <pre className="text-xs bg-muted/40 rounded-lg p-3 overflow-auto">
                {JSON.stringify(statusQuery.data ?? {}, null, 2)}
              </pre>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
