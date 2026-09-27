/**
 * Domicilio de la tienda web (27-sep-2026, regla de Diego):
 *   - pedido desde $30.000 → GRATIS
 *   - menos de $30.000 → $3.000 hasta 5 km a la redonda del local, $5.000 si es más lejos
 * (El PORTAL no cobra domicilio nunca: eso vive en apps/portal y en la API.)
 *
 * "A la redonda" = distancia en línea recta desde el pin oficial de la ficha de Google,
 * no la ruta en carro. La ubicación sale de Google Maps (GPS del celular o dirección
 * escogida en el autocompletado) y se guarda aquí para que carrito, pago y el botón de
 * WhatsApp usen EL MISMO dato y el mismo valor.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Pin oficial de la ficha de Google (FICHA_OFICIAL_UNICA.txt)
export const LOCAL = { lat: 4.8266652, lng: -75.6923926 };
export const GRATIS_DESDE = 30_000;
export const RADIO_CERCA_KM = 5;
export const TARIFA_CERCA = 3_000;
export const TARIFA_LEJOS = 5_000;
// Más allá de esto ya no es Pereira/Dosquebradas urbano: se confirma por WhatsApp
export const RADIO_MAX_KM = 15;

export function distanciaKm(lat: number, lng: number): number {
  const R = 6371;
  const rad = (g: number) => (g * Math.PI) / 180;
  const dLat = rad(lat - LOCAL.lat);
  const dLng = rad(lng - LOCAL.lng);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(LOCAL.lat)) * Math.cos(rad(lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

export type Domicilio =
  | { tipo: 'gratis'; valor: 0; texto: string }
  | { tipo: 'tarifa'; valor: number; texto: string }
  | { tipo: 'pendiente'; valor: null; texto: string };

/** Valor del domicilio. `km` null = todavía no sabemos dónde es. */
export function calcularDomicilio(subtotal: number, km: number | null): Domicilio {
  if (subtotal >= GRATIS_DESDE) return { tipo: 'gratis', valor: 0, texto: 'Gratis' };
  if (km == null) return { tipo: 'pendiente', valor: null, texto: 'Según tu ubicación' };
  if (km > RADIO_MAX_KM) return { tipo: 'pendiente', valor: null, texto: 'Por confirmar (fuera de zona)' };
  const valor = km <= RADIO_CERCA_KM ? TARIFA_CERCA : TARIFA_LEJOS;
  return { tipo: 'tarifa', valor, texto: `$${valor.toLocaleString('es-CO')}` };
}

export const REGLA_TEXTO = `Gratis desde $${GRATIS_DESDE.toLocaleString('es-CO')}. Si no: $${TARIFA_CERCA.toLocaleString('es-CO')} hasta ${RADIO_CERCA_KM} km del local y $${TARIFA_LEJOS.toLocaleString('es-CO')} más lejos.`;

export interface UbicacionEntrega {
  direccion: string;
  lat: number | null;
  lng: number | null;
  km: number | null;
  /** 'gps' = ubicación del celular · 'google' = dirección escogida en Maps · 'texto' = escrita a mano */
  fuente: 'gps' | 'google' | 'texto';
}

interface Estado {
  ubicacion: UbicacionEntrega | null;
  fijar: (u: UbicacionEntrega) => void;
  borrar: () => void;
}

export const useUbicacionEntrega = create<Estado>()(
  persist(
    (set) => ({
      ubicacion: null,
      fijar: (u) => set({ ubicacion: u }),
      borrar: () => set({ ubicacion: null }),
    }),
    { name: 'bp_ubicacion_entrega' },
  ),
);

/** Líneas para el mensaje de WhatsApp: dirección + enlace de Maps con el punto exacto. */
export function lineasUbicacion(u: UbicacionEntrega | null): string {
  if (!u || !u.direccion) return '\n📍 Dirección: (la envío por aquí)';
  let t = `\n📍 Dirección: ${u.direccion}`;
  if (u.lat != null && u.lng != null) {
    t += `\n🗺️ Ubicación: https://www.google.com/maps?q=${u.lat.toFixed(6)},${u.lng.toFixed(6)}`;
  }
  if (u.km != null) t += `\n📏 A ${u.km.toFixed(1).replace('.', ',')} km del local`;
  return t;
}
