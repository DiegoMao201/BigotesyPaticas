'use client';

import { useEffect, useRef, useState } from 'react';
import { MapPin, LocateFixed, Search } from 'lucide-react';
import { loadMapsScript } from '@/lib/maps';

const KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? '';
const DEFAULT_CENTER = { lat: 4.8087, lng: -75.6906 }; // Pereira, centro por defecto

interface Props {
  lat: number | null;
  lng: number | null;
  onChange: (lat: number, lng: number) => void;
  height?: number;
  className?: string;
}

/**
 * Mapa con marcador arrastrable + buscador de dirección — el aliado fija su
 * ubicación exacta. El pin visible SIEMPRE refleja lo que se va a guardar:
 * apenas el mapa carga, se dispara onChange con la posición inicial (antes
 * quedaba en null si el usuario nunca arrastraba el pin, aunque lo viera ahí).
 */
export function LocationPicker({ lat, lng, onChange, height = 280, className = '' }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // eslint-disable-next-line
  const markerRef = useRef<any>(null);
  // eslint-disable-next-line
  const mapObjRef = useRef<any>(null);
  const [ready, setReady] = useState(false);

  function movePin(position: { lat: number; lng: number }, zoom?: number) {
    if (markerRef.current) markerRef.current.setPosition(position);
    if (mapObjRef.current) {
      mapObjRef.current.setCenter(position);
      if (zoom) mapObjRef.current.setZoom(zoom);
    }
    onChange(position.lat, position.lng);
  }

  useEffect(() => {
    if (!KEY || !mapRef.current) return;
    const el = mapRef.current;
    const center = lat != null && lng != null ? { lat, lng } : DEFAULT_CENTER;

    loadMapsScript(KEY, () => {
      const map = new window.google.maps.Map(el, {
        center,
        zoom: lat != null ? 16 : 13,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        zoomControl: true,
      });
      const marker = new window.google.maps.Marker({
        position: center,
        map,
        draggable: true,
        animation: window.google.maps.Animation.DROP,
      });
      marker.addListener('dragend', () => {
        const pos = marker.getPosition();
        if (pos) onChange(pos.lat(), pos.lng());
      });
      map.addListener('click', (e: any) => {
        const pos = e.latLng;
        marker.setPosition(pos);
        onChange(pos.lat(), pos.lng());
      });
      markerRef.current = marker;
      mapObjRef.current = map;
      setReady(true);

      // Buscador de dirección (Places Autocomplete) — mismo patrón que
      // DeliveryZoneChecker en apps/store.
      if (inputRef.current) {
        const autocomplete = new window.google.maps.places.Autocomplete(inputRef.current, {
          bounds: new window.google.maps.LatLngBounds(
            new window.google.maps.LatLng(4.65, -75.85),
            new window.google.maps.LatLng(4.97, -75.55)
          ),
          componentRestrictions: { country: 'co' },
          fields: ['geometry', 'formatted_address', 'name'],
        });
        autocomplete.addListener('place_changed', () => {
          const place = autocomplete.getPlace();
          if (!place.geometry?.location) return;
          movePin({ lat: place.geometry.location.lat(), lng: place.geometry.location.lng() }, 17);
        });
      }

      // Garantiza que el pin visible siempre se guarde, aunque el usuario
      // nunca lo arrastre — antes se quedaba en null en ese caso.
      onChange(center.lat, center.lng);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function useMyLocation() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition((pos) => {
      movePin({ lat: pos.coords.latitude, lng: pos.coords.longitude }, 16);
    });
  }

  if (!KEY) {
    return (
      <div
        className={`rounded-xl border border-border bg-gray-50 flex flex-col items-center justify-center gap-2 text-center px-4 ${className}`}
        style={{ height }}
      >
        <MapPin className="h-6 w-6 text-muted" />
        <p className="text-xs text-muted">Mapa no disponible (falta configurar Google Maps)</p>
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="relative mb-2">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          placeholder="Busca tu dirección (ej. Cra 8 # 23-45, Pereira)"
          className="input-field pl-9"
        />
      </div>
      <div className="relative rounded-xl overflow-hidden border border-border">
        <div ref={mapRef} style={{ width: '100%', height }} />
        {ready && (
          <button
            type="button"
            onClick={useMyLocation}
            className="absolute bottom-3 right-3 inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-xs font-semibold text-primary-700 shadow-md border border-border hover:bg-primary-50"
          >
            <LocateFixed className="h-3.5 w-3.5" /> Mi ubicación
          </button>
        )}
        <p className="absolute top-3 left-3 bg-white/90 backdrop-blur rounded-lg px-2.5 py-1 text-[11px] text-muted shadow-sm">
          Arrastra el pin o toca el mapa para ajustar
        </p>
      </div>
    </div>
  );
}
