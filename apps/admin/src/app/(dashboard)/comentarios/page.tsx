'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MessageSquare, Eye, EyeOff, Trash2, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import { adminComments } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const TYPE_LABEL: Record<string, string> = { adoption: 'Adopción', lost: 'Perdido', found: 'Encontrado' };

function formatAgo(iso: string): string {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
  if (mins < 60) return `hace ${Math.max(1, mins)} min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.floor(hours / 24);
  return days === 1 ? 'ayer' : `hace ${days} días`;
}

export default function CommentsModerationPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'all' | 'visible' | 'hidden'>('all');
  const { data: comments = [], isLoading } = useQuery({
    queryKey: ['admin-comments', tab],
    queryFn: () => adminComments.list(tab),
    refetchInterval: 60_000,
  });
  const invalidate = () => qc.invalidateQueries({ queryKey: ['admin-comments'] });

  const { mutate: setStatus } = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'visible' | 'hidden' }) => adminComments.setStatus(id, status),
    onSuccess: (_, v) => { toast.success(v.status === 'hidden' ? 'Comentario oculto' : 'Comentario visible'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });
  const { mutate: remove } = useMutation({
    mutationFn: (id: string) => adminComments.remove(id),
    onSuccess: () => { toast.success('Comentario eliminado'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-6 p-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2"><MessageSquare className="h-6 w-6" /> Comentarios de la comunidad</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Lo que la gente escribe en las publicaciones de adopción, perdidos y encontrados de bigotesypaticas.com. Se publican al
          instante; aquí puedes ocultar o borrar lo que no corresponda.
        </p>
      </div>

      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        {([['all', 'Todos'], ['visible', 'Visibles'], ['hidden', 'Ocultos']] as const).map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${tab === k ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}>
            {label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <Card className="p-6 animate-pulse h-32" />
      ) : comments.length === 0 ? (
        <Card className="p-10 text-center text-gray-500">Todavía no hay comentarios.</Card>
      ) : (
        <div className="space-y-3">
          {comments.map((c) => (
            <Card key={c.id} className={`p-4 ${c.status === 'hidden' ? 'opacity-60' : ''}`}>
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap text-xs text-gray-500 mb-1">
                    <Badge className="bg-teal-50 text-teal-800">{TYPE_LABEL[c.entity_type] ?? c.entity_type}</Badge>
                    <a href={c.entity_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-teal-700 font-medium truncate max-w-xs">
                      {c.entity_title ?? c.entity_id} <ExternalLink className="h-3 w-3 shrink-0" />
                    </a>
                    <span>· {formatAgo(c.created_at)}</span>
                    {c.status === 'hidden' && <Badge className="bg-gray-200 text-gray-700">Oculto</Badge>}
                  </div>
                  <p className="text-sm"><span className="font-semibold text-gray-900">{c.author_name}:</span> <span className="text-gray-700 whitespace-pre-line">{c.body}</span></p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button size="sm" variant="outline" className="gap-1.5"
                    onClick={() => setStatus({ id: c.id, status: c.status === 'hidden' ? 'visible' : 'hidden' })}>
                    {c.status === 'hidden' ? <><Eye className="h-3.5 w-3.5" /> Mostrar</> : <><EyeOff className="h-3.5 w-3.5" /> Ocultar</>}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => { if (confirm('¿Eliminar este comentario?')) remove(c.id); }}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
