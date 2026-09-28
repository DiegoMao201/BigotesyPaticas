'use client';

/**
 * Intercepta TODOS los links de WhatsApp del admin (wa.me / api.whatsapp.com) y los
 * abre con openWhatsApp(): una sola pestaña reutilizada o la app de escritorio.
 * Así se arregla en todas las pantallas a la vez (pedidos, ventas, POS, citas,
 * reseñas…) sin tocar cada botón. Ver lib/whatsapp.ts.
 */
import { useEffect } from 'react';
import { openWhatsApp, parseWhatsAppLink } from '@/lib/whatsapp';

export function WhatsAppLinkInterceptor() {
  useEffect(() => {
    function onClick(e: MouseEvent) {
      // Respetar ctrl/cmd/shift-clic y clic central: el usuario pidió otra pestaña a propósito
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as HTMLElement | null)?.closest?.('a[href]') as HTMLAnchorElement | null;
      if (!a) return;
      const parsed = parseWhatsAppLink(a.href);
      if (!parsed) return;
      e.preventDefault();
      openWhatsApp(parsed.phone, parsed.text);
    }
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, []);
  return null;
}
