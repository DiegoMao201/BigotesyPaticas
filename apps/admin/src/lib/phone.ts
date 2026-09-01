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

// Colombia primero (default, es el negocio). El resto: toda Latinoamérica +
// Europa + Norteamérica + los países de Asia/Oceanía/África más comunes en
// clientes internacionales de e-commerce, ordenados alfabéticamente para
// que sea fácil de encontrar uno en el <select>.
export const PHONE_COUNTRIES: PhoneCountry[] = [
  { name: 'Colombia', dial: '57', flag: '🇨🇴' },

  // Latinoamérica y el Caribe
  { name: 'Argentina', dial: '54', flag: '🇦🇷' },
  { name: 'Bolivia', dial: '591', flag: '🇧🇴' },
  { name: 'Brasil', dial: '55', flag: '🇧🇷' },
  { name: 'Chile', dial: '56', flag: '🇨🇱' },
  { name: 'Costa Rica', dial: '506', flag: '🇨🇷' },
  { name: 'Cuba', dial: '53', flag: '🇨🇺' },
  { name: 'Ecuador', dial: '593', flag: '🇪🇨' },
  { name: 'El Salvador', dial: '503', flag: '🇸🇻' },
  { name: 'Guatemala', dial: '502', flag: '🇬🇹' },
  { name: 'Honduras', dial: '504', flag: '🇭🇳' },
  { name: 'México', dial: '52', flag: '🇲🇽' },
  { name: 'Nicaragua', dial: '505', flag: '🇳🇮' },
  { name: 'Panamá', dial: '507', flag: '🇵🇦' },
  { name: 'Paraguay', dial: '595', flag: '🇵🇾' },
  { name: 'Perú', dial: '51', flag: '🇵🇪' },
  { name: 'Puerto Rico', dial: '1', flag: '🇵🇷' },
  { name: 'República Dominicana', dial: '1', flag: '🇩🇴' },
  { name: 'Uruguay', dial: '598', flag: '🇺🇾' },
  { name: 'Venezuela', dial: '58', flag: '🇻🇪' },

  // Norteamérica
  { name: 'Canadá', dial: '1', flag: '🇨🇦' },
  { name: 'Estados Unidos', dial: '1', flag: '🇺🇸' },

  // Europa
  { name: 'Alemania', dial: '49', flag: '🇩🇪' },
  { name: 'Austria', dial: '43', flag: '🇦🇹' },
  { name: 'Bélgica', dial: '32', flag: '🇧🇪' },
  { name: 'Dinamarca', dial: '45', flag: '🇩🇰' },
  { name: 'España', dial: '34', flag: '🇪🇸' },
  { name: 'Finlandia', dial: '358', flag: '🇫🇮' },
  { name: 'Francia', dial: '33', flag: '🇫🇷' },
  { name: 'Grecia', dial: '30', flag: '🇬🇷' },
  { name: 'Irlanda', dial: '353', flag: '🇮🇪' },
  { name: 'Italia', dial: '39', flag: '🇮🇹' },
  { name: 'Noruega', dial: '47', flag: '🇳🇴' },
  { name: 'Países Bajos', dial: '31', flag: '🇳🇱' },
  { name: 'Polonia', dial: '48', flag: '🇵🇱' },
  { name: 'Portugal', dial: '351', flag: '🇵🇹' },
  { name: 'Reino Unido', dial: '44', flag: '🇬🇧' },
  { name: 'Rusia', dial: '7', flag: '🇷🇺' },
  { name: 'Suecia', dial: '46', flag: '🇸🇪' },
  { name: 'Suiza', dial: '41', flag: '🇨🇭' },

  // Asia, Oceanía y otros
  { name: 'Australia', dial: '61', flag: '🇦🇺' },
  { name: 'China', dial: '86', flag: '🇨🇳' },
  { name: 'Corea del Sur', dial: '82', flag: '🇰🇷' },
  { name: 'Emiratos Árabes Unidos', dial: '971', flag: '🇦🇪' },
  { name: 'Filipinas', dial: '63', flag: '🇵🇭' },
  { name: 'India', dial: '91', flag: '🇮🇳' },
  { name: 'Indonesia', dial: '62', flag: '🇮🇩' },
  { name: 'Israel', dial: '972', flag: '🇮🇱' },
  { name: 'Japón', dial: '81', flag: '🇯🇵' },
  { name: 'Malasia', dial: '60', flag: '🇲🇾' },
  { name: 'Marruecos', dial: '212', flag: '🇲🇦' },
  { name: 'Nueva Zelanda', dial: '64', flag: '🇳🇿' },
  { name: 'Singapur', dial: '65', flag: '🇸🇬' },
  { name: 'Sudáfrica', dial: '27', flag: '🇿🇦' },
  { name: 'Tailandia', dial: '66', flag: '🇹🇭' },
  { name: 'Turquía', dial: '90', flag: '🇹🇷' },
  { name: 'Vietnam', dial: '84', flag: '🇻🇳' },
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
