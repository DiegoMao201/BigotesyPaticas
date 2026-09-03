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
      const mb = (data.video_bytes / (1024 * 1024)).toFixed(1);
      if (data.mode === 'inbox') {
        toast.success(`Video (${mb} MB) enviado a la bandeja de TikTok. Ábrelo en la app para publicarlo.`);
      } else {
        toast.success(`Video (${mb} MB) publicado en TikTok (privacidad: ${data.privacy_level_used}).`);
      }
      setLastPublishId(data.publish_id);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const statusQuery = useQuery({
    queryKey: ['tiktok-publish-status', lastPublishId],
    queryFn: () => tiktok.publishStatus(lastPublishId!),
    enabled: !!lastPublishId,
    refetchInterval: (query) => {
      const s = String(query.state.data?.status ?? '');
      return s === 'PUBLISH_COMPLETE' || s === 'SEND_TO_USER_INBOX' || s === 'FAILED' ? false : 4000;
    },
  });

  const STATUS_LABEL: Record<string, string> = {
    PROCESSING_UPLOAD: 'Subiendo a TikTok…',
    PROCESSING_DOWNLOAD: 'TikTok está procesando el video…',
    SEND_TO_USER_INBOX: 'En tu bandeja de TikTok: ábrelo en la app para publicarlo',
    PUBLISH_COMPLETE: 'Publicado',
    FAILED: 'Falló',
  };

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
            Con los permisos actuales (<code>video.upload</code>) el video llega a la <strong>bandeja de borradores</strong> de
            la app de TikTok de la cuenta conectada y lo publicas con un toque. Cuando TikTok apruebe <code>video.publish</code>,
            este mismo botón publicará directo.
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
                <Badge className="bg-blue-100 text-blue-700">
                  {STATUS_LABEL[String(statusQuery.data?.status ?? '')] ?? String(statusQuery.data?.status ?? '...')}
                </Badge>
              </div>
              <pre className="text-xs bg-muted/40 rounded-lg p-3 overflow-auto">
                {JSON.stringify(statusQuery.data ?? {}, null, 2)}
              </pre>
            </div>
          )}
        </Card>
      )}

      {status?.connected && <AccountInventory onReconnect={() => connectMut.mutate()} />}
    </div>
  );
}

const nf = new Intl.NumberFormat('es-CO');

function AccountInventory({ onReconnect }: { onReconnect: () => void }) {
  const account = useQuery({ queryKey: ['tiktok-account'], queryFn: () => tiktok.account(), retry: false });
  const videos = useQuery({ queryKey: ['tiktok-videos'], queryFn: () => tiktok.videos(), retry: false });
  const needsReconnect = (e: unknown) => e instanceof Error && /video\.list|Reconectar/i.test(e.message);
  const u = account.data?.user;

  return (
    <Card className="p-5 space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h2 className="font-display font-semibold text-lg">Inventario de la cuenta</h2>
          <p className="text-xs text-muted-foreground max-w-2xl">
            Solo lectura: la API de TikTok no permite borrar ni editar videos ni el perfil. Aquí ves todo lo publicado con
            sus métricas para decidir qué limpiar; el botón <strong>Abrir en TikTok</strong> te lleva al video para borrarlo
            desde la app.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => { account.refetch(); videos.refetch(); }}>
          <RefreshCw className="h-4 w-4 mr-1" /> Actualizar
        </Button>
      </div>

      {account.isError && needsReconnect(account.error) && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm flex items-center justify-between gap-3 flex-wrap">
          <span>La cuenta se conectó con permisos viejos. Reconecta para autorizar el inventario (perfil y lista de videos).</span>
          <Button size="sm" onClick={onReconnect}>Reconectar ahora</Button>
        </div>
      )}
      {account.isError && !needsReconnect(account.error) && (
        <p className="text-sm text-destructive">{(account.error as Error).message}</p>
      )}

      {u && (
        <div className="flex items-center gap-4 flex-wrap">
          {u.avatar_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={u.avatar_url} alt="" className="h-14 w-14 rounded-full object-cover border border-border" />
          )}
          <div className="min-w-0">
            <p className="font-semibold">
              {u.display_name}{u.username ? <span className="text-muted-foreground font-normal"> · @{u.username}</span> : null}
            </p>
            {u.bio_description && <p className="text-xs text-muted-foreground whitespace-pre-line">{u.bio_description}</p>}
            {u.profile_deep_link && (
              <a href={u.profile_deep_link} target="_blank" rel="noreferrer" className="text-xs text-brand-700 underline">
                Abrir perfil en TikTok
              </a>
            )}
          </div>
          <div className="ml-auto grid grid-cols-4 gap-4 text-center">
            {[
              ['Videos', u.video_count],
              ['Seguidores', u.follower_count],
              ['Siguiendo', u.following_count],
              ['Me gusta', u.likes_count],
            ].map(([label, val]) => (
              <div key={String(label)}>
                <div className="text-lg font-bold tabular-nums">{typeof val === 'number' ? nf.format(val) : '—'}</div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {videos.isLoading && <p className="text-sm text-muted-foreground">Cargando videos…</p>}
      {videos.isError && !needsReconnect(videos.error) && (
        <p className="text-sm text-destructive">{(videos.error as Error).message}</p>
      )}
      {videos.data && (
        <div className="space-y-2">
          <p className="text-sm font-medium">{videos.data.count} videos públicos (más recientes primero)</p>
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="text-left p-2">Video</th>
                  <th className="text-left p-2">Fecha</th>
                  <th className="text-right p-2">Vistas</th>
                  <th className="text-right p-2">Me gusta</th>
                  <th className="text-right p-2">Coment.</th>
                  <th className="text-right p-2">Compart.</th>
                  <th className="p-2" />
                </tr>
              </thead>
              <tbody>
                {videos.data.videos.map((v) => (
                  <tr key={v.id} className="border-t border-border align-top">
                    <td className="p-2">
                      <div className="flex gap-3">
                        {v.cover_image_url && (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={v.cover_image_url} alt="" className="h-20 w-[45px] rounded object-cover bg-muted shrink-0" />
                        )}
                        <div className="min-w-0 max-w-md">
                          <p className="font-medium line-clamp-2">{v.title || v.video_description || '(sin título)'}</p>
                          {v.title && v.video_description && v.video_description !== v.title && (
                            <p className="text-xs text-muted-foreground line-clamp-2">{v.video_description}</p>
                          )}
                          {typeof v.duration === 'number' && (
                            <p className="text-[11px] text-muted-foreground">{v.duration}s</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="p-2 whitespace-nowrap text-muted-foreground">
                      {v.created_at ? new Date(v.created_at).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' }) : '—'}
                    </td>
                    <td className="p-2 text-right tabular-nums">{nf.format(v.view_count ?? 0)}</td>
                    <td className="p-2 text-right tabular-nums">{nf.format(v.like_count ?? 0)}</td>
                    <td className="p-2 text-right tabular-nums">{nf.format(v.comment_count ?? 0)}</td>
                    <td className="p-2 text-right tabular-nums">{nf.format(v.share_count ?? 0)}</td>
                    <td className="p-2 whitespace-nowrap">
                      {v.share_url && (
                        <a href={v.share_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-brand-700 underline">
                          <ExternalLink className="h-3 w-3" /> Abrir en TikTok
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Card>
  );
}
