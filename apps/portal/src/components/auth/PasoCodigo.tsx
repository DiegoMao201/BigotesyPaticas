'use client';

import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Loader2, Mail, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';

/**
 * Pasos del código al correo (8-nov-2026). Se usan en el ingreso (cédula + teléfono en
 * un celular nuevo) y en el aviso "agrega tu correo" con la sesión abierta.
 */

export function PasoCorreo({
  titulo = 'Agrega tu correo',
  texto = 'Para proteger tu cuenta, te enviaremos un código cada vez que entres desde un celular nuevo.',
  inicial = '',
  onEnviar,
  onVolver,
}: {
  titulo?: string;
  texto?: string;
  inicial?: string;
  onEnviar: (correo: string) => Promise<void>;
  onVolver?: () => void;
}) {
  const [correo, setCorreo] = useState(inicial);
  const [cargando, setCargando] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (!/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(correo.trim())) {
      toast.error('Escribe un correo válido');
      return;
    }
    setCargando(true);
    try {
      await onEnviar(correo.trim().toLowerCase());
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <motion.form onSubmit={enviar} className="flex flex-col gap-3" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-50 text-primary-700">
        <Mail className="h-6 w-6" />
      </div>
      <h2 className="font-display text-xl font-bold text-gray-900">{titulo}</h2>
      <p className="-mt-1 text-sm text-gray-500">{texto}</p>
      <div className="relative">
        <Mail className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder="tucorreo@gmail.com"
          value={correo}
          onChange={(e) => setCorreo(e.target.value)}
          className="input-field pl-10"
          autoFocus
        />
      </div>
      <button type="submit" disabled={cargando} className="btn-primary mt-1 py-4 text-base">
        {cargando ? <Loader2 className="h-5 w-5 animate-spin" /> : <>Enviarme el código <ArrowRight className="h-5 w-5" /></>}
      </button>
      {onVolver && (
        <button type="button" onClick={onVolver} className="py-2 text-sm font-semibold text-gray-500">
          Volver
        </button>
      )}
    </motion.form>
  );
}

export function PasoCodigo({
  hint,
  onVerificar,
  onReenviar,
  onVolver,
}: {
  hint: string;
  onVerificar: (codigo: string) => Promise<void>;
  onReenviar: () => Promise<void>;
  onVolver?: () => void;
}) {
  const [codigo, setCodigo] = useState('');
  const [cargando, setCargando] = useState(false);
  const [espera, setEspera] = useState(30);
  const enviando = useRef(false);

  useEffect(() => {
    if (espera <= 0) return;
    const t = setTimeout(() => setEspera((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [espera]);

  async function verificar(valor = codigo) {
    if (valor.length !== 6 || enviando.current) return;
    enviando.current = true;
    setCargando(true);
    try {
      await onVerificar(valor);
    } catch (err) {
      toast.error((err as Error).message);
      setCodigo('');
    } finally {
      enviando.current = false;
      setCargando(false);
    }
  }

  async function reenviar() {
    try {
      await onReenviar();
      setEspera(30);
      toast.success('Te mandamos un código nuevo');
    } catch (err) {
      toast.error((err as Error).message);
    }
  }

  return (
    <motion.form
      onSubmit={(e) => { e.preventDefault(); verificar(); }}
      className="flex flex-col gap-3"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-50 text-primary-700">
        <ShieldCheck className="h-6 w-6" />
      </div>
      <h2 className="font-display text-xl font-bold text-gray-900">Revisa tu correo</h2>
      <p className="-mt-1 text-sm text-gray-500">
        Te enviamos un código de 6 números a <span className="font-semibold text-gray-700">{hint}</span>. Si no lo ves, mira en Spam o Promociones.
      </p>
      <input
        type="text"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        placeholder="••••••"
        value={codigo}
        onChange={(e) => {
          const v = e.target.value.replace(/\D/g, '').slice(0, 6);
          setCodigo(v);
          if (v.length === 6) verificar(v);
        }}
        className="input-field text-center font-display text-2xl tracking-[0.5em]"
        autoFocus
      />
      <button type="submit" disabled={cargando || codigo.length !== 6} className="btn-primary mt-1 py-4 text-base">
        {cargando ? <Loader2 className="h-5 w-5 animate-spin" /> : <>Entrar <ArrowRight className="h-5 w-5" /></>}
      </button>
      <button type="button" onClick={reenviar} disabled={espera > 0} className="py-2 text-sm font-semibold text-primary-700 disabled:text-gray-400">
        {espera > 0 ? `Reenviar código en ${espera} s` : 'Reenviar código'}
      </button>
      <p className="text-center text-xs text-gray-400">
        ¿No te llega? Entra con Google o escríbenos al{' '}
        <a href="https://wa.me/573206876633" className="font-semibold text-primary-700">WhatsApp 320 687 6633</a>
      </p>
      {onVolver && (
        <button type="button" onClick={onVolver} className="py-1 text-sm font-semibold text-gray-500">
          Volver
        </button>
      )}
    </motion.form>
  );
}
