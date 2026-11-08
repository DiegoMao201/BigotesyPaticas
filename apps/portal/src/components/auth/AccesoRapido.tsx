'use client';

import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Fingerprint, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { entrarConPasskey, google, passkeysDisponibles } from '@/lib/passkeys';
import type { LoginResponse } from '@/lib/api';


/**
 * Botones de acceso sin escribir nada (8-nov-2026): huella/Face ID y Google.
 * El de Google solo aparece cuando la API tiene un client ID configurado; el de huella,
 * solo si el celular la soporta. La primera vez con Google se pide la cédula y el
 * teléfono para unir la cuenta (`linkRequerido`).
 */
export function AccesoRapido({
  onLogin,
  onLinkRequerido,
}: {
  onLogin: (r: LoginResponse) => void;
  onLinkRequerido: (token: string, email: string | null) => void;
}) {
  const [huella, setHuella] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [googleId, setGoogleId] = useState<string | null>(null);
  const caja = useRef<HTMLDivElement>(null);

  useEffect(() => {
    passkeysDisponibles().then(setHuella);
    google.config().then((c) => setGoogleId(c.client_id)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!googleId || !caja.current) return;
    const pintar = () => {
      (window as any).google?.accounts.id.initialize({
        client_id: googleId,
        callback: async ({ credential }: { credential: string }) => {
          try {
            const r = await google.login<Omit<LoginResponse, 'status'> & { status: string; link_token?: string; email?: string }>(credential);
            if (r.status === 'link_required' && r.link_token) onLinkRequerido(r.link_token, r.email ?? null);
            else onLogin(r as LoginResponse);
          } catch (e) {
            toast.error((e as Error).message);
          }
        },
        ux_mode: 'popup',
        use_fedcm_for_prompt: true,
      });
      (window as any).google?.accounts.id.renderButton(caja.current, {
        theme: 'outline', size: 'large', shape: 'pill', text: 'continue_with', locale: 'es', width: caja.current!.offsetWidth || 320,
      });
    };
    if ((window as any).google?.accounts) return pintar();
    const s = document.createElement('script');
    s.src = 'https://accounts.google.com/gsi/client';
    s.async = true;
    s.onload = pintar;
    document.head.appendChild(s);
  }, [googleId, onLogin, onLinkRequerido]);

  async function conHuella() {
    setCargando(true);
    try {
      onLogin(await entrarConPasskey<LoginResponse>());
    } catch (e) {
      const m = (e as Error).message || '';
      if (!/abort|cancel|NotAllowed/i.test(m + (e as Error).name)) toast.error(m || 'No pudimos verificar tu huella');
    } finally {
      setCargando(false);
    }
  }

  if (!huella && !googleId) return null;
  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-center gap-3 text-xs text-gray-400">
        <span className="h-px flex-1 bg-gray-100" /> o entra sin escribir <span className="h-px flex-1 bg-gray-100" />
      </div>
      {huella && (
        <motion.button
          type="button"
          whileTap={{ scale: 0.97 }}
          onClick={conHuella}
          disabled={cargando}
          className="flex h-12 items-center justify-center gap-2 rounded-full border-2 border-gray-900 text-sm font-bold text-gray-900"
        >
          {cargando ? <Loader2 className="h-5 w-5 animate-spin" /> : <Fingerprint className="h-5 w-5" />}
          Entrar con huella o Face ID
        </motion.button>
      )}
      {googleId && <div ref={caja} className="flex min-h-[44px] justify-center" />}
    </div>
  );
}
