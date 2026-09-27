'use client';

/**
 * Ubicación de entrega con Google Maps (27-sep-2026). Diego: "importantísimo que el
 * mensaje del pedido de WhatsApp lleve la dirección de la API de Maps, para eso la
 * conectamos: que nos den su ubicación… y que el cálculo del domicilio se calcule bien".
 *
 * Dos formas de darla, las dos con coordenadas:
 *   1. "Usar mi ubicación actual": GPS del celular → Geocoder la vuelve dirección.
 *   2. Escribir y ESCOGER una sugerencia de Google (Places Autocomplete con geometry).
 * Con las coordenadas se mide la distancia al local (lib/delivery) y el valor sale solo.
 * Si Maps no carga o la persona no escoge sugerencia, la dirección escrita igual viaja
 * en el mensaje y el domicilio queda "por confirmar": nunca bloquea un pedido.
 */
import { useEffect, useRef, useState } from 'react';
import { Crosshair, Loader2, MapPin, Pencil } from 'lucide-react';
import { loadMapsScript } from '@/lib/maps';
import { distanciaKm, useUbicacionEntrega, calcularDomicilio } from '@/lib/delivery';

const MAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? '';

export function DeliveryLocationPicker({ subtotal }: { subtotal: number }) {
  const { ubicacion, fijar } = useUbicacionEntrega();
  const inputRef = useRef<HTMLInputElement>(null);
  const [texto, setTexto] = useState('');
  const [editando, setEditando] = useState(true);
  const [montado, setMontado] = useState(false);
  // La ubicación guardada vive en el navegador: se decide qué mostrar ya montado,
  // para que el HTML del servidor y el del cliente coincidan.
  useEffect(() => {
    setMontado(true);
    if (useUbicacionEntrega.getState().ubicacion) setEditando(false);
  }, []);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState('');
  const [armado, setArmado] = useState(false);

  // Autocompletado de Google (se carga solo cuando la persona toca el campo)
  useEffect(() => {
    if (!armado || !editando || !MAPS_KEY || !inputRef.current) return;
    loadMapsScript(MAPS_KEY, () => {
      if (!inputRef.current || !window.google?.maps?.places) return;
      const ac = new window.google.maps.places.Autocomplete(inputRef.current, {
        bounds: new window.google.maps.LatLngBounds(
          new window.google.maps.LatLng(4.65, -75.85),
          new window.google.maps.LatLng(4.97, -75.55),
        ),
        componentRestrictions: { country: 'co' },
        fields: ['geometry', 'formatted_address', 'name'],
      });
      ac.addListener('place_changed', () => {
        const p = ac.getPlace();
        const loc = p?.geometry?.location;
        if (!loc) return;
        const lat = loc.lat(), lng = loc.lng();
        const nombre = p.name && !(p.formatted_address ?? '').startsWith(p.name) ? `${p.name}, ` : '';
        fijar({ direccion: `${nombre}${p.formatted_address ?? ''}`.trim(), lat, lng, km: distanciaKm(lat, lng), fuente: 'google' });
        setTexto('');
        setEditando(false);
        setError('');
      });
    });
  }, [armado, editando, fijar]);

  function usarGPS() {
    if (!navigator.geolocation) { setError('Tu navegador no permite ubicación. Escribe tu dirección.'); return; }
    setOcupado(true);
    setError('');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude, lng = pos.coords.longitude;
        const base = { lat, lng, km: distanciaKm(lat, lng), fuente: 'gps' as const };
        if (!MAPS_KEY) { fijar({ ...base, direccion: 'Ubicación compartida' }); setOcupado(false); setEditando(false); return; }
        loadMapsScript(MAPS_KEY, () => {
          try {
            new window.google.maps.Geocoder().geocode({ location: { lat, lng } }, (res: any[], st: string) => {
              fijar({ ...base, direccion: st === 'OK' && res?.[0] ? res[0].formatted_address : 'Ubicación compartida' });
              setOcupado(false);
              setEditando(false);
            });
          } catch {
            fijar({ ...base, direccion: 'Ubicación compartida' });
            setOcupado(false);
            setEditando(false);
          }
        });
      },
      (err) => {
        setOcupado(false);
        setError(err.code === 1
          ? 'No diste permiso de ubicación. Actívalo o escribe tu dirección abajo.'
          : 'No pudimos obtener tu ubicación. Escribe tu dirección abajo.');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    );
  }

  // Dirección escrita sin escoger sugerencia: viaja igual, sin coordenadas
  function guardarTexto() {
    const t = texto.trim();
    if (t.length < 6) return;
    fijar({ direccion: t, lat: null, lng: null, km: null, fuente: 'texto' });
    setEditando(false);
  }

  const dom = calcularDomicilio(subtotal, ubicacion?.km ?? null);
  if (!montado) return <div className="h-28" />;

  if (ubicacion && !editando) {
    return (
      <div className="rounded-2xl border border-[#187f77]/30 bg-[#187f77]/5 p-4">
        <div className="flex items-start gap-3">
          <MapPin className="h-5 w-5 text-[#187f77] shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900 leading-snug">{ubicacion.direccion}</p>
            <p className="text-xs text-gray-600 mt-1">
              {ubicacion.km != null
                ? `A ${ubicacion.km.toFixed(1).replace('.', ',')} km del local · Domicilio: ${dom.texto}`
                : 'Sin ubicación en el mapa · el domicilio te lo confirmamos por WhatsApp'}
            </p>
          </div>
          <button
            type="button"
            onClick={() => { setEditando(true); setArmado(true); }}
            className="shrink-0 inline-flex items-center gap-1 text-xs font-semibold text-[#187f77] px-2 py-1 rounded-lg hover:bg-white"
          >
            <Pencil className="h-3.5 w-3.5" /> Cambiar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={usarGPS}
        disabled={ocupado}
        className="w-full h-12 rounded-2xl bg-[#187f77] text-white font-bold flex items-center justify-center gap-2 active:scale-[0.99] disabled:opacity-70"
      >
        {ocupado ? <Loader2 className="h-5 w-5 animate-spin" /> : <Crosshair className="h-5 w-5" />}
        {ocupado ? 'Buscando tu ubicación…' : 'Usar mi ubicación actual'}
      </button>
      <div className="flex items-center gap-3 text-xs text-gray-400">
        <span className="h-px flex-1 bg-gray-200" /> o escribe tu dirección <span className="h-px flex-1 bg-gray-200" />
      </div>
      <div className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          onFocus={() => setArmado(true)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); guardarTexto(); } }}
          placeholder="Barrio, calle y número"
          autoComplete="street-address"
          className="flex-1 min-w-0 rounded-xl border border-border px-4 h-12 text-base focus:outline-none focus:ring-2 focus:ring-brand/50"
        />
        {texto.trim().length >= 6 && (
          <button type="button" onClick={guardarTexto} className="shrink-0 px-4 h-12 rounded-xl border border-border text-sm font-semibold">
            Usar
          </button>
        )}
      </div>
      <p className="text-xs text-gray-500">Escoge tu dirección de la lista de Google para calcular el domicilio exacto.</p>
      {error && <p className="text-xs text-amber-700">{error}</p>}
      {ubicacion && (
        <button type="button" onClick={() => { setEditando(false); }} className="text-xs text-gray-500 underline">
          Dejar la anterior
        </button>
      )}
    </div>
  );
}
