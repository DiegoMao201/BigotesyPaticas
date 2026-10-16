'use client';

/**
 * Dirección en otra ciudad + cotización por transportadora (16-oct-2026).
 *
 * El orden es el que sigue una persona: primero DÓNDE (puede escribir la dirección
 * y escogerla de Google, que rellena ciudad, departamento y código postal), después
 * CUÁNTO (un botón que pregunta a las transportadoras) y por último CON QUIÉN (elige
 * una tarifa). Hasta que no elige, no hay total y no hay botón de pagar.
 *
 * Si Google Maps no carga, los campos siguen siendo campos: se escriben a mano y
 * el servidor valida la ciudad contra el catálogo de Envia (código DANE).
 */
import { useEffect, useRef, useState } from 'react';
import { Loader2, MapPin, Truck } from 'lucide-react';
import { loadMapsScript } from '@/lib/maps';
import { formatCurrency } from '@/lib/utils';
import {
  DEPARTAMENTOS, codigoDepartamento, huellaCotizacion, useEnvioNacional,
  type DestinoNacional, type TarifaEnvio,
} from '@/lib/envio-nacional';

const MAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? '';

type Props = {
  items: { productId: string; quantity: number }[];
  onCambiarALocal: () => void;
  /** Se marca en rojo lo que falta cuando la persona intenta pagar sin terminar. */
  pideDatos?: boolean;
};

type Respuesta = {
  ok: boolean;
  local?: boolean;
  destino?: { ciudad: string; departamento: string; departamento_nombre: string; postal: string };
  tarifas?: TarifaEnvio[];
  peso_kg?: number;
  mensaje?: string | null;
  detail?: string | { mensaje?: string };
};

const campo =
  'w-full rounded-xl border border-border px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/50';

export function EnvioNacional({ items, onCambiarALocal, pideDatos }: Props) {
  const { destino, tarifa, cotizadoPara, setDestino, setTarifa } = useEnvioNacional();
  const [tarifas, setTarifas] = useState<TarifaEnvio[]>([]);
  const [cotizando, setCotizando] = useState(false);
  const [error, setError] = useState('');
  const [esLocal, setEsLocal] = useState('');
  const [peso, setPeso] = useState<number | null>(null);
  const [montado, setMontado] = useState(false);
  const [armado, setArmado] = useState(false);
  const dirRef = useRef<HTMLInputElement>(null);

  useEffect(() => setMontado(true), []);

  const huella = huellaCotizacion(items, destino);
  // La tarifa elegida solo vale si el carrito y la ciudad son los mismos de cuando
  // se cotizó. Si cambió algo, se pide de nuevo: el peso cambia el precio.
  const tarifaVigente = tarifa && cotizadoPara === huella ? tarifa : null;
  const listo = destino.departamento && destino.ciudad.trim().length >= 2 && destino.calle.trim().length >= 6;

  // Autocompletado de Google: toda Colombia, sin el límite de Pereira–Dosquebradas
  // que usa el domicilio local. Rellena los campos pero no los bloquea.
  useEffect(() => {
    if (!armado || !MAPS_KEY || !dirRef.current) return;
    loadMapsScript(MAPS_KEY, () => {
      if (!dirRef.current || !window.google?.maps?.places) return;
      const ac = new window.google.maps.places.Autocomplete(dirRef.current, {
        componentRestrictions: { country: 'co' },
        fields: ['address_components', 'formatted_address', 'geometry'],
      });
      ac.addListener('place_changed', () => {
        const p = ac.getPlace();
        const comps: { long_name: string; short_name: string; types: string[] }[] = p?.address_components ?? [];
        const get = (t: string) => comps.find((c) => c.types.includes(t))?.long_name ?? '';
        const route = get('route');
        const numero = get('street_number');
        const ciudad = get('locality') || get('administrative_area_level_2');
        const depto = get('administrative_area_level_1');
        const cod = codigoDepartamento(depto) ?? (ciudad && codigoDepartamento(ciudad)) ?? '';
        const loc = p?.geometry?.location;
        setDestino({
          calle: route ? (numero ? `${route} # ${numero}` : route) : (p?.formatted_address ?? '').split(',')[0],
          barrio: get('sublocality') || get('sublocality_level_1') || get('neighborhood') || destino.barrio,
          ciudad: ciudad || destino.ciudad,
          departamento: cod || destino.departamento,
          departamento_nombre: DEPARTAMENTOS.find((d) => d.codigo === cod)?.nombre ?? destino.departamento_nombre,
          postal: get('postal_code') || '',
          lat: loc ? loc.lat() : null,
          lng: loc ? loc.lng() : null,
        });
      });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [armado]);

  async function cotizar() {
    if (!listo) return;
    setCotizando(true);
    setError('');
    setEsLocal('');
    setTarifas([]);
    try {
      const r = await fetch('/api/v1/public/shipping/quote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: items.map((i) => ({ product_id: i.productId, quantity: i.quantity })),
          destino: {
            departamento: destino.departamento,
            ciudad: destino.ciudad.trim(),
            calle: destino.calle.trim(),
            barrio: destino.barrio.trim() || null,
            referencia: destino.referencia.trim() || null,
            postal: destino.postal.trim() || null,
            lat: destino.lat,
            lng: destino.lng,
          },
        }),
      });
      const d: Respuesta = await r.json();
      if (!r.ok) {
        const det = d.detail;
        setError(typeof det === 'string' ? det : det?.mensaje ?? 'No pudimos cotizar el envío. Intenta de nuevo.');
        return;
      }
      if (d.local) {
        setEsLocal(d.mensaje ?? '');
        return;
      }
      if (d.destino) {
        setDestino({ ciudad: d.destino.ciudad, departamento_nombre: d.destino.departamento_nombre, postal: d.destino.postal || destino.postal });
      }
      const lista = d.tarifas ?? [];
      setTarifas(lista);
      setPeso(d.peso_kg ?? null);
      if (lista.length === 0) setError(d.mensaje ?? 'Ninguna transportadora nos dio tarifa para esa ciudad.');
      // La más barata queda elegida de una vez; se puede cambiar con un toque.
      if (lista[0]) setTarifa(lista[0], huellaCotizacion(items, { ...destino, ciudad: d.destino?.ciudad ?? destino.ciudad }));
    } catch {
      setError('No pudimos conectar con las transportadoras. Revisa tu conexión e intenta de nuevo.');
    } finally {
      setCotizando(false);
    }
  }

  if (!montado) return <div className="h-40" />;

  const falta = (v: string, min = 1) => pideDatos && v.trim().length < min;

  return (
    <div className="space-y-4">
      <div className="rounded-2xl bg-[#187f77]/5 border border-[#187f77]/20 p-3 text-xs text-[#0d4a45] leading-relaxed">
        <Truck className="h-4 w-4 inline mr-1 -mt-0.5" aria-hidden="true" />
        Enviamos a toda Colombia por transportadora. Escribe tu dirección, cotiza y elige
        con quién quieres que llegue. El envío se paga junto con el pedido.
      </div>

      <div>
        <label htmlFor="n-direccion" className="text-xs font-medium text-muted-foreground block mb-1">
          Dirección de entrega
        </label>
        <div className="relative">
          <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#187f77]" aria-hidden="true" />
          <input
            ref={dirRef}
            id="n-direccion"
            type="text"
            value={destino.calle}
            onChange={(e) => setDestino({ calle: e.target.value })}
            onFocus={() => setArmado(true)}
            placeholder="Calle 100 # 15-20"
            autoComplete="street-address"
            className={`${campo} pl-9 ${falta(destino.calle, 6) ? 'border-amber-400 ring-2 ring-amber-200' : ''}`}
          />
        </div>
        <p className="text-[11px] text-muted-foreground mt-1">
          Escríbela y escógela de la lista de Google: así se llena sola la ciudad.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="n-depto" className="text-xs font-medium text-muted-foreground block mb-1">Departamento</label>
          <select
            id="n-depto"
            value={destino.departamento}
            onChange={(e) => {
              const cod = e.target.value;
              setDestino({ departamento: cod, departamento_nombre: DEPARTAMENTOS.find((d) => d.codigo === cod)?.nombre ?? '' });
            }}
            className={`${campo} bg-white ${falta(destino.departamento) ? 'border-amber-400 ring-2 ring-amber-200' : ''}`}
          >
            <option value="">Elige…</option>
            {DEPARTAMENTOS.map((d) => (
              <option key={d.codigo} value={d.codigo}>{d.nombre}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="n-ciudad" className="text-xs font-medium text-muted-foreground block mb-1">Ciudad o municipio</label>
          <input
            id="n-ciudad"
            type="text"
            value={destino.ciudad}
            onChange={(e) => setDestino({ ciudad: e.target.value })}
            placeholder="Bogotá, Medellín, Cali…"
            autoComplete="address-level2"
            className={`${campo} ${falta(destino.ciudad, 2) ? 'border-amber-400 ring-2 ring-amber-200' : ''}`}
          />
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="n-barrio" className="text-xs font-medium text-muted-foreground block mb-1">Barrio</label>
          <input id="n-barrio" type="text" value={destino.barrio} onChange={(e) => setDestino({ barrio: e.target.value })} placeholder="Chapinero" className={campo} />
        </div>
        <div>
          <label htmlFor="n-ref" className="text-xs font-medium text-muted-foreground block mb-1">Apartamento, torre o indicaciones</label>
          <input id="n-ref" type="text" value={destino.referencia} onChange={(e) => setDestino({ referencia: e.target.value })} placeholder="Apto 301, torre 2" className={campo} />
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="n-cedula" className="text-xs font-medium text-muted-foreground block mb-1">Cédula de quien recibe <span className="opacity-60">(opcional)</span></label>
          <input id="n-cedula" type="text" inputMode="numeric" value={destino.cedula} onChange={(e) => setDestino({ cedula: e.target.value })} placeholder="La pide la transportadora al entregar" className={campo} />
        </div>
        <div>
          <label htmlFor="n-email" className="text-xs font-medium text-muted-foreground block mb-1">Correo <span className="opacity-60">(opcional)</span></label>
          <input id="n-email" type="email" value={destino.email} onChange={(e) => setDestino({ email: e.target.value })} placeholder="Para enviarte la guía" autoComplete="email" className={campo} />
        </div>
      </div>

      {/* Cotizar */}
      <button
        type="button"
        onClick={cotizar}
        disabled={!listo || cotizando}
        className="w-full h-12 rounded-2xl bg-[#187f77] text-white font-bold flex items-center justify-center gap-2 active:scale-[0.99] disabled:opacity-50"
      >
        {cotizando ? <Loader2 className="h-5 w-5 animate-spin" /> : <Truck className="h-5 w-5" />}
        {cotizando
          ? 'Preguntando a las transportadoras…'
          : tarifaVigente
            ? 'Volver a cotizar'
            : `Cotizar envío${destino.ciudad.trim() ? ` a ${destino.ciudad.trim()}` : ''}`}
      </button>
      {pideDatos && !tarifaVigente && listo && !cotizando && (
        <p className="text-sm font-medium text-amber-700">Cotiza el envío y elige una transportadora para poder pagar.</p>
      )}

      {esLocal && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          <p>{esLocal}</p>
          <button type="button" onClick={onCambiarALocal} className="mt-2 font-semibold underline">
            Usar domicilio propio en Pereira o Dosquebradas
          </button>
        </div>
      )}
      {error && <p className="text-sm text-amber-700">{error}</p>}

      {/* Las tarifas */}
      {tarifas.length > 0 && (
        <div className="space-y-2" role="radiogroup" aria-label="Transportadora">
          <p className="text-sm font-semibold">
            ¿Con quién lo enviamos?
            {peso != null && <span className="font-normal text-muted-foreground"> · paquete de {peso.toLocaleString('es-CO')} kg</span>}
          </p>
          {tarifas.map((t) => {
            const activa = tarifaVigente?.carrier === t.carrier && tarifaVigente?.service === t.service;
            return (
              <button
                key={`${t.carrier}-${t.service}`}
                type="button"
                role="radio"
                aria-checked={activa}
                onClick={() => setTarifa(t, huella)}
                className={`w-full rounded-2xl border-2 p-3.5 text-left transition-colors ${
                  activa ? 'border-[#187f77] bg-[#187f77]/5' : 'border-border hover:border-[#187f77]/40'
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold leading-tight">{t.carrier_nombre}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {t.service_nombre} · {t.dias}
                      {t.fecha_estimada ? ` · llega aprox. el ${fechaCorta(t.fecha_estimada)}` : ''}
                    </p>
                  </div>
                  <p className="font-bold tabular-nums shrink-0">{formatCurrency(t.precio)}</p>
                </div>
              </button>
            );
          })}
          <p className="text-[11px] text-muted-foreground">
            El tiempo lo estima la transportadora en días hábiles desde que recoge el paquete.
          </p>
        </div>
      )}
    </div>
  );
}

function fechaCorta(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m || !d) return iso;
  return new Date(y, m - 1, d).toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short' });
}

export type { DestinoNacional };
