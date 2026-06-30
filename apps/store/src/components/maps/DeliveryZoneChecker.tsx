'use client';

import { useEffect, useRef, useState } from 'react';
import { MapPin, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { BUSINESS_INFO } from '@/lib/business-info';
import { loadMapsScript } from '@/lib/maps';

const MAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? '';
const STORE_LAT = BUSINESS_INFO.geo.latitude;
const STORE_LNG = BUSINESS_INFO.geo.longitude;
const MAX_KM = 22;

type Status = 'idle' | 'loading' | 'ok' | 'far' | 'error';

export function DeliveryZoneChecker() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<Status>('idle');
  const [distanceText, setDistanceText] = useState('');
  const [durationText, setDurationText] = useState('');
  const [placeAddress, setPlaceAddress] = useState('');

  useEffect(() => {
    if (!MAPS_KEY) return;
    loadMapsScript(MAPS_KEY, () => {
      if (!inputRef.current) return;
      const autocomplete = new window.google.maps.places.Autocomplete(inputRef.current, {
        bounds: new window.google.maps.LatLngBounds(
          new window.google.maps.LatLng(4.65, -75.85),
          new window.google.maps.LatLng(4.97, -75.55),
        ),
        componentRestrictions: { country: 'co' },
        fields: ['geometry', 'formatted_address', 'name'],
      });

      autocomplete.addListener('place_changed', () => {
        const place = autocomplete.getPlace();
        if (!place.geometry?.location) return;
        setStatus('loading');
        setPlaceAddress(place.formatted_address ?? place.name ?? '');

        const svc = new window.google.maps.DistanceMatrixService();
        svc.getDistanceMatrix(
          {
            origins: [{ lat: STORE_LAT, lng: STORE_LNG }],
            destinations: [place.geometry.location],
            travelMode: window.google.maps.TravelMode.DRIVING,
            unitSystem: window.google.maps.UnitSystem.METRIC,
          },
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (result: any, st: string) => {
            if (st !== 'OK' || !result) { setStatus('error'); return; }
            const el = result.rows[0]?.elements[0];
            if (el?.status !== 'OK') { setStatus('error'); return; }
            const km = (el.distance?.value ?? 99999) / 1000;
            setDistanceText(el.distance?.text ?? '');
            setDurationText(el.duration?.text ?? '');
            setStatus(km <= MAX_KM ? 'ok' : 'far');
          },
        );
      });
    });
  }, []);

  const waMsg = encodeURIComponent(
    `Hola! Quiero hacer un pedido con domicilio a: ${placeAddress}. ¿Pueden entregarme?`,
  );

  return (
    <div className="rounded-2xl border border-border bg-card p-6 space-y-4">
      <div>
        <p className="font-display font-bold text-base">¿Llegamos a tu zona?</p>
        <p className="text-sm text-muted-foreground mt-0.5">Escribe tu dirección y te confirmamos al instante</p>
      </div>

      <div className="relative">
        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          placeholder="Tu dirección en Pereira o Dosquebradas..."
          className="w-full pl-10 pr-4 py-3 rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-brand-300 text-sm"
          disabled={status === 'loading'}
        />
      </div>

      {status === 'loading' && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Verificando cobertura…
        </div>
      )}

      {status === 'ok' && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4 space-y-3">
          <div className="flex items-start gap-3">
            <CheckCircle className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-emerald-800 text-sm">
                ¡Sí llegamos! — {distanceText} · {durationText} desde la tienda
              </p>
              <p className="text-emerald-700 text-xs mt-0.5">Entrega 24-72h · Gratis desde $30.000 COP</p>
            </div>
          </div>
          <a
            href={`https://wa.me/573206876633?text=${waMsg}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-green-500 text-white font-semibold text-sm hover:bg-green-600 transition-colors"
          >
            💬 Pedir por WhatsApp ahora
          </a>
        </div>
      )}

      {status === 'far' && (
        <div className="rounded-xl bg-amber-50 border border-amber-200 p-4">
          <div className="flex items-start gap-3">
            <XCircle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-800 text-sm">Por ahora cubrimos Pereira y Dosquebradas</p>
              <p className="text-amber-700 text-xs mt-1">
                Escríbenos — a veces podemos coordinar entregas especiales.
              </p>
            </div>
          </div>
          <a
            href={`https://wa.me/573206876633?text=${waMsg}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full mt-3 py-2.5 rounded-xl bg-amber-500 text-white font-semibold text-sm hover:bg-amber-600 transition-colors"
          >
            💬 Consultar de todas formas
          </a>
        </div>
      )}

      {status === 'error' && (
        <p className="text-sm text-red-600">No pudimos verificar la dirección. Intenta de nuevo.</p>
      )}
    </div>
  );
}
