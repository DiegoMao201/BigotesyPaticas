/**
 * Teléfonos con código de país para clientes internacionales.
 *
 * Antes de esto, TODO el admin (POS, reseñas, citas, invitaciones al
 * portal, moderación de adopción) le anteponía "57" a ciegas a cualquier
 * teléfono para armar el link de wa.me, sin importar si el número ya
 * traía su propio código de país. Un cliente de España/Chile/Ecuador/
 * Venezuela/EE.UU. que compra por el store para entrega en Colombia
 * terminaba con un link de WhatsApp roto.
 *
 * Convención de almacenamiento (crm.customers.phone, String(40), sin
 * constraint de formato — ver migraciones): los números colombianos
 * siguen igual que siempre, 10 dígitos SIN prefijo (compatibilidad total
 * con los ya guardados); los de cualquier otro país se guardan con "+"
 * y su código de país completo, ej. "+34612345678".
 */

export interface PhoneCountry {
  name: string;
  dial: string; // sin "+"
  flag: string;
}

// Colombia primero (default). El resto son los países que el dueño del
// negocio reportó que ya le escriben clientes reales, más algunos vecinos
// frecuentes de Latinoamérica.
export const PHONE_COUNTRIES: PhoneCountry[] = [
  { name: 'Colombia', dial: '57', flag: '🇨🇴' },
  { name: 'España', dial: '34', flag: '🇪🇸' },
  { name: 'Chile', dial: '56', flag: '🇨🇱' },
  { name: 'Ecuador', dial: '593', flag: '🇪🇨' },
  { name: 'Venezuela', dial: '58', flag: '🇻🇪' },
  { name: 'Estados Unidos', dial: '1', flag: '🇺🇸' },
  { name: 'México', dial: '52', flag: '🇲🇽' },
  { name: 'Perú', dial: '51', flag: '🇵🇪' },
  { name: 'Argentina', dial: '54', flag: '🇦🇷' },
  { name: 'Panamá', dial: '507', flag: '🇵🇦' },
  { name: 'Costa Rica', dial: '506', flag: '🇨🇷' },
  { name: 'República Dominicana', dial: '1', flag: '🇩🇴' },
  { name: 'Canadá', dial: '1', flag: '🇨🇦' },
  { name: 'Brasil', dial: '55', flag: '🇧🇷' },
];

// Códigos únicos, del más largo al más corto, para no confundir "593" con
// un falso match de "5" al parsear un número guardado.
const DIAL_CODES = Array.from(new Set(PHONE_COUNTRIES.map((c) => c.dial))).sort(
  (a, b) => b.length - a.length
);

/**
 * Convierte un teléfono guardado (legado CO de 10 dígitos, o "+<país><num>")
 * a los dígitos que espera wa.me. Solo antepone "57" cuando el número tiene
 * pinta de celular colombiano legado (10 dígitos, sin "+") — si ya trae su
 * propio código de país, se respeta tal cual.
 */
export function toWhatsAppDigits(phone: string | null | undefined): string {
  const raw = (phone ?? '').trim();
  if (!raw) return '';
  const hadPlus = raw.startsWith('+');
  const digits = raw.replace(/\D/g, '');
  if (hadPlus) return digits;
  if (digits.length === 10) return `57${digits}`;
  return digits;
}

/** Arma la URL de wa.me respetando el código de país real del teléfono. */
export function buildWhatsAppUrl(phone: string | null | undefined, text?: string): string {
  const digits = toWhatsAppDigits(phone);
  const query = text ? `?text=${encodeURIComponent(text)}` : '';
  return digits ? `https://wa.me/${digits}${query}` : `https://wa.me/${query}`;
}

/** Separa un teléfono guardado en {dial, local} para prellenar un formulario. */
export function parsePhoneForForm(phone: string | null | undefined): { dial: string; local: string } {
  const raw = (phone ?? '').trim();
  if (!raw) return { dial: '57', local: '' };
  if (raw.startsWith('+')) {
    const digits = raw.replace(/\D/g, '');
    const match = DIAL_CODES.find((d) => digits.startsWith(d));
    return match ? { dial: match, local: digits.slice(match.length) } : { dial: '57', local: digits };
  }
  return { dial: '57', local: raw.replace(/\D/g, '') };
}

/** Compone el valor a guardar en customer.phone a partir del formulario. */
export function composePhone(dial: string, local: string): string {
  const digits = local.replace(/\D/g, '');
  if (!digits) return '';
  return dial === '57' ? digits : `+${dial}${digits}`;
}
