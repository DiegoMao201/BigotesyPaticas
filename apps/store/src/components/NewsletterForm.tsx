'use client';

import { useState } from 'react';

export function NewsletterForm() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'ok' | 'error'>('idle');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setStatus('loading');
    try {
      const res = await fetch('/api/v1/contact/newsletter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      });
      if (!res.ok) throw new Error();
      setStatus('ok');
      setEmail('');
    } catch {
      setStatus('error');
    }
  }

  if (status === 'ok') {
    return (
      <div className="flex flex-col items-center gap-2 py-4">
        <div className="text-4xl">🎉</div>
        <p className="text-white font-semibold text-lg">¡Estás dentro del club!</p>
        <p className="text-white/80 text-sm">Revisa tu correo — te enviamos un cupón de bienvenida.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 justify-center max-w-md mx-auto">
      <input
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="tu@email.com"
        className="flex-1 px-5 py-3 rounded-2xl bg-white/20 backdrop-blur-sm border border-white/30 text-white placeholder:text-white/60 focus:outline-none focus:ring-2 focus:ring-white/50"
      />
      <button
        type="submit"
        disabled={status === 'loading'}
        className="px-6 py-3 rounded-2xl bg-white text-brand-600 font-bold hover:bg-white/90 transition-colors shadow-md disabled:opacity-70"
      >
        {status === 'loading' ? 'Enviando…' : 'Suscribirme 🎁'}
      </button>
      {status === 'error' && (
        <p className="text-red-200 text-xs text-center col-span-2">Error al suscribirte. Intenta de nuevo.</p>
      )}
    </form>
  );
}
