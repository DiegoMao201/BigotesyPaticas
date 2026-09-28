/**
 * Abrir WhatsApp desde el admin SIN tumbar la sesión (Diego 28-sep-2026: "el envío
 * de WhatsApp me reinicia sesión o se me sale de mi computador").
 *
 * La causa: cada botón abría `wa.me` en una pestaña NUEVA. WhatsApp Web solo
 * permite una pestaña activa, así que cada una nueva desplazaba a la anterior
 * ("WhatsApp está abierto en otra ventana") y la sesión se caía.
 *
 * Ahora todo pasa por aquí, con dos modos que el admin elige una vez:
 *  - 'app'  → la app de escritorio de WhatsApp (whatsapp://send). No toca el navegador.
 *  - 'web'  → WhatsApp Web en UNA sola pestaña con nombre fijo, que se reutiliza.
 */
import { toWhatsAppDigits } from '@/lib/phone';

export type WhatsAppMode = 'app' | 'web';

const KEY = 'bp_whatsapp_mode';
const WINDOW_NAME = 'bp_whatsapp';

export function getWhatsAppMode(): WhatsAppMode {
  try {
    return localStorage.getItem(KEY) === 'app' ? 'app' : 'web';
  } catch {
    return 'web';
  }
}

export function setWhatsAppMode(mode: WhatsAppMode) {
  try {
    localStorage.setItem(KEY, mode);
  } catch {
    /* sin storage: queda el modo por defecto */
  }
}

/** `phone` puede venir guardado de cualquier forma (+57…, 10 dígitos, vacío). */
export function openWhatsApp(phone: string | null | undefined, text?: string, mode = getWhatsAppMode()) {
  const digits = toWhatsAppDigits(phone);
  const params = new URLSearchParams();
  if (digits) params.set('phone', digits);
  if (text) params.set('text', text);
  const qs = params.toString();

  if (mode === 'app') {
    window.location.href = `whatsapp://send${qs ? `?${qs}` : ''}`;
    return;
  }
  // Pestaña con nombre fijo: si ya existe, se reutiliza en vez de abrir otra.
  const w = window.open(`https://web.whatsapp.com/send${qs ? `?${qs}` : ''}`, WINDOW_NAME);
  w?.focus();
}

/** Lee un link wa.me / api.whatsapp.com y devuelve {phone, text}, o null si no lo es. */
export function parseWhatsAppLink(href: string): { phone: string; text?: string } | null {
  let url: URL;
  try {
    url = new URL(href);
  } catch {
    return null;
  }
  const host = url.hostname.replace(/^www\./, '');
  if (host === 'wa.me') {
    return { phone: url.pathname.replace(/\D/g, ''), text: url.searchParams.get('text') ?? undefined };
  }
  if (host === 'api.whatsapp.com' || host === 'web.whatsapp.com') {
    return {
      phone: (url.searchParams.get('phone') ?? '').replace(/\D/g, ''),
      text: url.searchParams.get('text') ?? undefined,
    };
  }
  return null;
}

/** Copia el texto al portapapeles (respaldo si WhatsApp no abre). */
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
