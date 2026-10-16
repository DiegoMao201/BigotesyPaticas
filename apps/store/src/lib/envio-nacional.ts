/**
 * Envío a otra ciudad de Colombia por transportadora (16-oct-2026).
 *
 * Diego: "quiero hacer envíos fuera de mi cobertura local [...] el cliente mira
 * cuánto le cuesta el envío y lo paga de una vez".
 *
 * El domicilio propio (Pereira y Dosquebradas) sigue en `lib/delivery.ts`, intacto.
 * Esto es el otro camino: la persona dice a qué ciudad va, el servidor le pregunta a
 * las transportadoras (Coordinadora, Servientrega, Inter Rapidísimo, TCC) y ella
 * elige con cuál y cuánto paga. Ese valor entra al total y se cobra en línea.
 *
 * Se guarda en el navegador el MODO y el DESTINO, para que si vuelve del pago no
 * tenga que escribir todo otra vez. Las tarifas NO se guardan: caducan, y lo que se
 * cobra es lo que la transportadora diga en el momento de crear el pedido.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ModoEnvio = 'local' | 'nacional';

export interface DestinoNacional {
  /** Código de 2 letras que espera Envia: DC, AN, VC… */
  departamento: string;
  departamento_nombre: string;
  ciudad: string;
  calle: string;
  barrio: string;
  referencia: string;
  postal: string;
  cedula: string;
  email: string;
  /** Quién recibe, si no es quien compra. */
  recibe: string;
  lat: number | null;
  lng: number | null;
}

export interface TarifaEnvio {
  carrier: string;
  carrier_nombre: string;
  service: string;
  service_nombre: string;
  precio: number;
  dias: string;
  fecha_estimada: string | null;
  dias_numero: number | null;
}

/** Copia de la lista de Envia (`GET /state?country_code=CO`, 16-oct-2026). */
export const DEPARTAMENTOS: { codigo: string; nombre: string }[] = [
  { codigo: 'AM', nombre: 'Amazonas' }, { codigo: 'AN', nombre: 'Antioquia' },
  { codigo: 'AR', nombre: 'Arauca' }, { codigo: 'AT', nombre: 'Atlántico' },
  { codigo: 'DC', nombre: 'Bogotá D.C.' }, { codigo: 'BL', nombre: 'Bolívar' },
  { codigo: 'BY', nombre: 'Boyacá' }, { codigo: 'CL', nombre: 'Caldas' },
  { codigo: 'CA', nombre: 'Caquetá' }, { codigo: 'CS', nombre: 'Casanare' },
  { codigo: 'CU', nombre: 'Cauca' }, { codigo: 'CE', nombre: 'Cesar' },
  { codigo: 'CH', nombre: 'Chocó' }, { codigo: 'CO', nombre: 'Córdoba' },
  { codigo: 'CN', nombre: 'Cundinamarca' }, { codigo: 'GU', nombre: 'Guainía' },
  { codigo: 'GA', nombre: 'Guaviare' }, { codigo: 'HU', nombre: 'Huila' },
  { codigo: 'LG', nombre: 'La Guajira' }, { codigo: 'MA', nombre: 'Magdalena' },
  { codigo: 'ME', nombre: 'Meta' }, { codigo: 'NA', nombre: 'Nariño' },
  { codigo: 'NS', nombre: 'Norte de Santander' }, { codigo: 'PU', nombre: 'Putumayo' },
  { codigo: 'QU', nombre: 'Quindío' }, { codigo: 'RI', nombre: 'Risaralda' },
  { codigo: 'SA', nombre: 'San Andrés y Providencia' }, { codigo: 'SN', nombre: 'Santander' },
  { codigo: 'SU', nombre: 'Sucre' }, { codigo: 'TO', nombre: 'Tolima' },
  { codigo: 'VC', nombre: 'Valle del Cauca' }, { codigo: 'VA', nombre: 'Vaupés' },
  { codigo: 'VI', nombre: 'Vichada' },
];

const sinTildes = (s: string) =>
  s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

/** "Bogotá", "Bogota D.C.", "Valle del Cauca" → código de Envia. */
export function codigoDepartamento(nombre: string): string | null {
  const n = sinTildes(nombre);
  if (!n) return null;
  if (n.startsWith('bogota') || n.includes('distrito capital')) return 'DC';
  if (n.startsWith('san andres')) return 'SA';
  const hit = DEPARTAMENTOS.find((d) => sinTildes(d.nombre) === n || sinTildes(d.nombre).startsWith(n));
  return hit?.codigo ?? null;
}

export const DESTINO_VACIO: DestinoNacional = {
  departamento: '', departamento_nombre: '', ciudad: '', calle: '', barrio: '',
  referencia: '', postal: '', cedula: '', email: '', recibe: '', lat: null, lng: null,
};

interface Estado {
  modo: ModoEnvio;
  destino: DestinoNacional;
  tarifa: TarifaEnvio | null;
  /** Huella de (carrito + ciudad) con la que se cotizó: si cambia, la tarifa ya no vale. */
  cotizadoPara: string;
  setModo: (m: ModoEnvio) => void;
  setDestino: (d: Partial<DestinoNacional>) => void;
  setTarifa: (t: TarifaEnvio | null, huella: string) => void;
}

export const useEnvioNacional = create<Estado>()(
  persist(
    (set) => ({
      modo: 'local',
      destino: DESTINO_VACIO,
      tarifa: null,
      cotizadoPara: '',
      setModo: (modo) => set({ modo }),
      // Cambiar la ciudad o el departamento invalida la tarifa (cambia el precio);
      // corregir el apartamento o la cédula, no: sería obligar a cotizar otra vez
      // por un detalle que la transportadora no cobra.
      setDestino: (d) =>
        set((s) => {
          const destino = { ...s.destino, ...d };
          const cambiaRuta =
            (d.ciudad !== undefined && sinTildes(d.ciudad) !== sinTildes(s.destino.ciudad)) ||
            (d.departamento !== undefined && d.departamento !== s.destino.departamento);
          return cambiaRuta ? { destino, tarifa: null, cotizadoPara: '' } : { destino };
        }),
      setTarifa: (tarifa, cotizadoPara) => set({ tarifa, cotizadoPara }),
    }),
    {
      name: 'bp_envio_nacional',
      // Las tarifas no sobreviven a una recarga: se vuelven a pedir.
      partialize: (s) => ({ modo: s.modo, destino: s.destino }) as unknown as Estado,
    },
  ),
);

/** Huella del carrito + destino: lo único que cambia el precio de un envío. */
export function huellaCotizacion(items: { productId: string; quantity: number }[], d: DestinoNacional): string {
  return JSON.stringify([items.map((i) => [i.productId, i.quantity]), d.departamento, sinTildes(d.ciudad)]);
}
