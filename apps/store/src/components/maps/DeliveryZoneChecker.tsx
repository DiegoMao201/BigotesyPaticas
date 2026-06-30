'use client';

import { useEffect, useRef, useState } from 'react';
import { MapPin, CheckCircle, XCircle, Loader2, Navigation } from 'lucide-react';
import { BUSINESS_INFO } from '@/lib/business-info';
import { loadMapsScript } from '@/lib/maps';

const MAPS_KEY  = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? '';
const STORE_LAT = BUSINESS_INFO.geo.latitude;
const STORE_LNG = BUSINESS_INFO.geo.longitude;
const MAX_KM    = 22;

type Status = 'idle' | 'locating' | 'loading' | 'ok' | 'far' | 'error';

export function DeliveryZoneChecker() {
  const inputRef      = useRef<HTMLInputElement>(null);
  const [status, setStatus]           = useState<Status>('idle');
  const [distanceText, setDistanceText] = useState('');
  const [durationText, setDurationText] = useState('');
  const [placeAddress, setPlaceAddress] = useState('');
  const [geoError, setGeoError]         = useState('');

  // ── Calcula desde coordenadas o lugar ─────────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  function calcDistance(destination: any) {
    setStatus('loading');
    const svc = new window.google.maps.DistanceMatrixService();
    svc.getDistanceMatrix(
      {
        origins:      [{ lat: STORE_LAT, lng: STORE_LNG }],
        destinations: [destination],
        travelMode:   window.google.maps.TravelMode.DRIVING,
        unitSystem:   window.google.maps.UnitSystem.METRIC,
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
  }

  // ── Reverse geocode coordenadas → dirección legible ───────────────────────
  function reverseGeocode(lat: number, lng: number) {
    const geocoder = new window.google.maps.Geocoder();
    geocoder.geocode(
      { location: { lat, lng } },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (results: any[], st: string) => {
        if (st === 'OK' && results[0]) {
          const addr = results[0].formatted_address;
          setPlaceAddress(addr);
          if (inputRef.current) inputRef.current.value = addr;
        }
        calcDistance({ lat, lng });
      },
    );
  }

  // ── Detectar ubicación del dispositivo ────────────────────────────────────
  function detectLocation() {
    if (!navigator.geolocation) {
      setGeoError('Tu navegador no soporta geolocalización');
      return;
    }
    setStatus('locating');
    setGeoError('');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        loadMapsScript(MAPS_KEY, () =>
          reverseGeocode(pos.coords.latitude, pos.coords.longitude)
        );
      },
      (err) => {
        setStatus('idle');
        if (err.code === 1) setGeoError('Permite el acceso a tu ubicación y vuelve a intentarlo');
        else setGeoError('No pudimos obtener tu ubicación. Escribe tu dirección manualmente.');
      },
      { timeout: 8000, maximumAge: 60000 },
    );
  }

  // ── Autocomplete manual ───────────────────────────────────────────────────
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
        setPlaceAddress(place.formatted_address ?? place.name ?? '');
        calcDistance(place.geometry.location);
      });
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const waMsg = encodeURIComponent(
    `Hola! Quiero hacer un pedido con domicilio a: ${placeAddress}. ¿Pueden entregarme?`,
  );

  const isChecking = status === 'locating' || status === 'loading';

  return (
    <div className="rounded-2xl border border-border bg-card p-6 space-y-4">
      <div>
        <p className="font-display font-bold text-base">¿Llegamos a tu zona?</p>
        <p className="text-sm text-muted-foreground mt-0.5">
          Usa tu ubicación o escribe tu dirección
        </p>
      </div>

      {/* Botón ubicación automática */}
      <button
        onClick={detectLocation}
        disabled={isChecking}
        className="flex items-center gap-2.5 w-full px-4 py-3 rounded-xl bg-brand-600 text-white font-semibold text-sm hover:bg-brand-700 active:scale-[.98] transition-all disabled:opacity-60 disabled:cursor-not-allowed shadow-sm"
      >
        {status === 'locating'
          ? <Loader2 className="h-4 w-4 animate-spin shrink-0" />
          : <Navigation className="h-4 w-4 shrink-0" />
        }
        {status === 'locating' ? 'Detectando tu ubicación…' : '📍 Usar mi ubicación actual'}
      </button>

      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <div className="flex-1 h-px bg-border" />
        <span>o escribe tu dirección</span>
        <div className="flex-1 h-px bg-border" />
      </div>

      {/* Input dirección manual */}
      <div className="relative">
        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          placeholder="Ej: Cra 13 #25-40, Pereira..."
          className="w-full pl-10 pr-4 py-3 rounded-xl border border-border bg-background focus:outline-none focus:ring-2 focus:ring-brand-300 text-sm"
          disabled={isChecking}
        />
      </div>

      {/* Estados */}
      {status === 'loading' && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Calculando cobertura…
        </div>
      )}

      {geoError && (
        <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-xl p-3">
          {geoError}
        </p>
      )}

      {status === 'ok' && (
        <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4 space-y-3">
          <div className="flex items-start gap-3">
            <CheckCircle className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-emerald-800 text-sm">
                ✅ ¡Sí llegamos! — {distanceText} · {durationText} desde la tienda
              </p>
              <p className="text-emerald-700 text-xs mt-0.5">
                Entrega 24-72h hábiles · Gratis desde $30.000 COP
              </p>
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
              <p className="font-semibold text-amber-800 text-sm">
                Por ahora cubrimos Pereira y Dosquebradas
              </p>
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
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl p-3">
          No pudimos verificar la dirección. Intenta de nuevo o escríbenos por WhatsApp.
        </p>
      )}
    </div>
  );
}
