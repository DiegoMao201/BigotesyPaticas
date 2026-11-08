'use client';

import { useState } from 'react';

export function FormEliminar() {
  const [doc, setDoc] = useState('');
  const [tel, setTel] = useState('');
  const [estado, setEstado] = useState<'' | 'enviando' | 'listo' | 'error'>('');
  const [msg, setMsg] = useState('');

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setEstado('enviando');
    try {
      const r = await fetch('/api/v1/portal/auth/delete-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: doc, phone: tel }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.detail || 'Error');
      setMsg(d.message); setEstado('listo');
    } catch {
      setEstado('error');
    }
  }

  if (estado === 'listo') {
    return <p className="mt-6 rounded-2xl bg-teal-50 p-5 text-sm text-teal-800">{msg}</p>;
  }
  return (
    <form onSubmit={enviar} className="mt-6 space-y-3">
      <label className="block text-sm font-semibold">
        Cédula con la que te registraste
        <input required value={doc} onChange={(e) => setDoc(e.target.value)} inputMode="numeric" className="mt-1 w-full rounded-xl border border-border px-4 py-3" />
      </label>
      <label className="block text-sm font-semibold">
        Teléfono registrado
        <input required value={tel} onChange={(e) => setTel(e.target.value)} inputMode="tel" className="mt-1 w-full rounded-xl border border-border px-4 py-3" />
      </label>
      <button disabled={estado === 'enviando'} className="w-full rounded-full bg-red-600 py-3.5 font-bold text-white disabled:opacity-50">
        {estado === 'enviando' ? 'Enviando…' : 'Pedir la eliminación de mi cuenta'}
      </button>
      {estado === 'error' && <p className="text-sm text-red-600">No pudimos enviar la solicitud. Escríbenos por WhatsApp al 320 687 6633.</p>}
    </form>
  );
}
