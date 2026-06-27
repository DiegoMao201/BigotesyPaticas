'use client';

import { useState } from 'react';
import { Send, CheckCircle } from 'lucide-react';

export function ContactForm() {
  const [form, setForm] = useState({ name: '', email: '', phone: '', message: '' });
  const [status, setStatus] = useState<'idle' | 'loading' | 'ok' | 'error'>('idle');

  function update(k: keyof typeof form, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus('loading');
    try {
      const res = await fetch('/api/v1/contact/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error();
      setStatus('ok');
    } catch {
      setStatus('error');
    }
  }

  if (status === 'ok') {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <CheckCircle className="h-16 w-16 text-teal-600" />
        <h3 className="text-2xl font-display font-bold">¡Mensaje enviado!</h3>
        <p className="text-muted-foreground max-w-sm">
          Recibimos tu mensaje. Te responderemos muy pronto al correo <strong>{form.email}</strong>.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium mb-1.5 block">Nombre *</label>
          <input
            type="text" required value={form.name}
            onChange={(e) => update('name', e.target.value)}
            placeholder="Tu nombre"
            className="w-full px-4 py-3 rounded-2xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-brand-300 text-sm"
          />
        </div>
        <div>
          <label className="text-sm font-medium mb-1.5 block">Teléfono</label>
          <input
            type="tel" value={form.phone}
            onChange={(e) => update('phone', e.target.value)}
            placeholder="+57 320 687 6633"
            className="w-full px-4 py-3 rounded-2xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-brand-300 text-sm"
          />
        </div>
      </div>
      <div>
        <label className="text-sm font-medium mb-1.5 block">Correo electrónico *</label>
        <input
          type="email" required value={form.email}
          onChange={(e) => update('email', e.target.value)}
          placeholder="tu@correo.com"
          className="w-full px-4 py-3 rounded-2xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-brand-300 text-sm"
        />
      </div>
      <div>
        <label className="text-sm font-medium mb-1.5 block">Mensaje *</label>
        <textarea
          required rows={5} value={form.message}
          onChange={(e) => update('message', e.target.value)}
          placeholder="¿En qué podemos ayudarte?"
          className="w-full px-4 py-3 rounded-2xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-brand-300 text-sm resize-none"
        />
      </div>
      {status === 'error' && (
        <p className="text-sm text-red-600">No se pudo enviar el mensaje. Intenta de nuevo.</p>
      )}
      <button
        type="submit" disabled={status === 'loading'}
        className="w-full flex items-center justify-center gap-2 py-3 px-6 rounded-2xl gradient-brand text-white font-semibold text-sm shadow-glow hover:opacity-90 transition-opacity disabled:opacity-60"
      >
        {status === 'loading' ? 'Enviando…' : <><Send className="h-4 w-4" /> Enviar mensaje</>}
      </button>
    </form>
  );
}
