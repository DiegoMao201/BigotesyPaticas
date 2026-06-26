'use client';

import { useState } from 'react';
import { Phone, Mail, MapPin, Send, CheckCircle } from 'lucide-react';

function ContactForm() {
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
            type="text"
            required
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
            placeholder="Tu nombre"
            className="w-full px-4 py-3 rounded-2xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-brand-300 text-sm"
          />
        </div>
        <div>
          <label className="text-sm font-medium mb-1.5 block">Teléfono</label>
          <input
            type="tel"
            value={form.phone}
            onChange={(e) => update('phone', e.target.value)}
            placeholder="+57 320 687 6633"
            className="w-full px-4 py-3 rounded-2xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-brand-300 text-sm"
          />
        </div>
      </div>
      <div>
        <label className="text-sm font-medium mb-1.5 block">Correo electrónico *</label>
        <input
          type="email"
          required
          value={form.email}
          onChange={(e) => update('email', e.target.value)}
          placeholder="tu@correo.com"
          className="w-full px-4 py-3 rounded-2xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-brand-300 text-sm"
        />
      </div>
      <div>
        <label className="text-sm font-medium mb-1.5 block">Mensaje *</label>
        <textarea
          required
          rows={5}
          value={form.message}
          onChange={(e) => update('message', e.target.value)}
          placeholder="¿En qué podemos ayudarte?"
          className="w-full px-4 py-3 rounded-2xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-brand-300 text-sm resize-none"
        />
      </div>
      {status === 'error' && (
        <p className="text-sm text-red-600">No se pudo enviar el mensaje. Intenta de nuevo.</p>
      )}
      <button
        type="submit"
        disabled={status === 'loading'}
        className="w-full flex items-center justify-center gap-2 py-3 px-6 rounded-2xl gradient-brand text-white font-semibold text-sm shadow-glow hover:opacity-90 transition-opacity disabled:opacity-60"
      >
        {status === 'loading' ? (
          'Enviando…'
        ) : (
          <>
            <Send className="h-4 w-4" /> Enviar mensaje
          </>
        )}
      </button>
    </form>
  );
}

export default function ContactoPage() {
  return (
    <div className="container-tight py-16">
      <div className="mb-10">
        <p className="text-brand-600 font-semibold text-sm mb-1">Estamos aquí para ti</p>
        <h1 className="text-4xl md:text-5xl font-display font-extrabold mb-3">Contáctanos</h1>
        <p className="text-muted-foreground text-lg max-w-md">
          ¿Tienes preguntas sobre un producto, un pedido o quieres conocer más?
          Escríbenos y te respondemos pronto.
        </p>
      </div>

      <div className="grid md:grid-cols-5 gap-10">
        {/* Info */}
        <div className="md:col-span-2 space-y-6">
          <div className="rounded-2xl bg-teal-50 border border-teal-100 p-6 space-y-4">
            <h2 className="font-display font-bold text-lg text-teal-900">Información de contacto</h2>
            <ul className="space-y-3 text-sm text-teal-800">
              <li className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-teal-700 flex items-center justify-center text-white shrink-0">
                  <Phone className="h-4 w-4" />
                </div>
                <a href="tel:+573206876633" className="hover:underline font-medium">+57 320 687 6633</a>
              </li>
              <li className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-teal-700 flex items-center justify-center text-white shrink-0 mt-0.5">
                  <Mail className="h-4 w-4" />
                </div>
                <a href="mailto:bigotesypaticasdosquebradas@gmail.com" className="hover:underline break-all">
                  bigotesypaticasdosquebradas@gmail.com
                </a>
              </li>
              <li className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-teal-700 flex items-center justify-center text-white shrink-0">
                  <MapPin className="h-4 w-4" />
                </div>
                <span>Dosquebradas, Risaralda</span>
              </li>
            </ul>
          </div>

          <div className="rounded-2xl border border-border bg-card p-6 space-y-3">
            <h3 className="font-display font-semibold">Zona de entrega</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Entregamos en toda la <strong>zona urbana de Pereira y Dosquebradas</strong>.
              Envío gratis en compras desde $30.000.
            </p>
            <div className="text-sm text-muted-foreground">🕐 Tiempo de entrega: <strong>24-72 horas</strong></div>
          </div>

          <a
            href="https://wa.me/573206876633?text=Hola!%20Tengo%20una%20pregunta%20sobre%20Bigotes%20y%20Paticas"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-5 py-3 rounded-2xl bg-green-500 text-white font-semibold text-sm hover:bg-green-600 transition-colors shadow-md w-full justify-center"
          >
            <span className="text-lg">💬</span> Chatear por WhatsApp
          </a>
        </div>

        {/* Form */}
        <div className="md:col-span-3">
          <div className="rounded-3xl border border-border bg-card p-8">
            <h2 className="font-display font-bold text-xl mb-6">Envíanos un mensaje</h2>
            <ContactForm />
          </div>
        </div>
      </div>
    </div>
  );
}
