'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { MessageCircle, Send, Loader2 } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || '';

interface Comment {
  id: string;
  author_name: string;
  body: string;
  created_at: string;
}

function timeAgo(iso: string) {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
  if (mins < 1) return 'ahora';
  if (mins < 60) return `hace ${mins} min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'ayer';
  return `hace ${days} días`;
}

/**
 * Comentarios públicos (sin cuenta) en una publicación de la comunidad.
 * Se cargan en el cliente para que la página siga siendo estática/ISR y los
 * comentarios nuevos aparezcan al instante sin esperar la revalidación.
 */
export function CommentsSection({
  entityType,
  entityId,
  accent = '#187f77',
  placeholder = 'Escribe un mensaje…',
  initialComments = [],
}: {
  entityType: 'adoption' | 'lost' | 'found';
  entityId: string;
  accent?: string;
  placeholder?: string;
  initialComments?: Comment[];
}) {
  const [comments, setComments] = useState<Comment[]>(initialComments);
  const [name, setName] = useState('');
  const [body, setBody] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem('byp_comment_name');
      if (saved) setName(saved);
    } catch {}
    fetch(`${API_BASE}/v1/public/community/comments/${entityType}/${entityId}`, { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : []))
      .then((data: Comment[]) => Array.isArray(data) && setComments(data))
      .catch(() => {});
  }, [entityType, entityId]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(false);
    const n = name.trim();
    const b = body.trim();
    if (n.length < 2) return setError('Escribe tu nombre');
    if (b.length < 2) return setError('Escribe un mensaje');
    setSending(true);
    try {
      const res = await fetch(`${API_BASE}/v1/public/community/comments/${entityType}/${entityId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ author_name: n, body: b }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(typeof data?.detail === 'string' ? data.detail : 'No se pudo publicar el comentario');
        return;
      }
      setComments((prev) => [data as Comment, ...prev]);
      setBody('');
      setOk(true);
      try { localStorage.setItem('byp_comment_name', n); } catch {}
    } catch {
      setError('No se pudo publicar el comentario, intenta de nuevo');
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="mt-10" aria-labelledby="comentarios">
      <h2 id="comentarios" className="text-xl font-display font-bold mb-4 flex items-center gap-2">
        <MessageCircle className="h-5 w-5" style={{ color: accent }} />
        Comentarios {comments.length > 0 && <span className="text-sm font-normal text-muted-foreground">({comments.length})</span>}
      </h2>

      <form onSubmit={submit} className="rounded-2xl border border-border bg-card p-4 mb-6 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-[200px_1fr] gap-3">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={80}
            placeholder="Tu nombre"
            aria-label="Tu nombre"
            className="rounded-xl border border-border bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2"
            style={{ ['--tw-ring-color' as string]: accent }}
          />
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            maxLength={500}
            rows={2}
            placeholder={placeholder}
            aria-label="Comentario"
            className="rounded-xl border border-border bg-background px-3 py-2.5 text-sm resize-y min-h-[44px] focus:outline-none focus:ring-2"
            style={{ ['--tw-ring-color' as string]: accent }}
          />
        </div>
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <p className="text-[11px] text-muted-foreground">
            {error ? <span className="text-red-600 font-medium">{error}</span> : ok ? <span className="text-emerald-700 font-medium">¡Comentario publicado! 💛</span> : `${body.length}/500 · Sin enlaces, con cariño.`}
          </p>
          <button
            type="submit"
            disabled={sending}
            className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold text-white transition-opacity disabled:opacity-60"
            style={{ backgroundColor: accent }}
          >
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            Comentar
          </button>
        </div>
      </form>

      {comments.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sé la primera persona en dejar un mensaje. 🐾</p>
      ) : (
        <ul className="space-y-3">
          {comments.map((c) => (
            <li key={c.id} className="rounded-2xl border border-border bg-card p-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0" style={{ backgroundColor: accent }}>
                  {c.author_name.charAt(0).toUpperCase()}
                </span>
                <span className="font-semibold text-sm">{c.author_name}</span>
                <span className="text-xs text-muted-foreground">· {timeAgo(c.created_at)}</span>
              </div>
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{c.body}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
