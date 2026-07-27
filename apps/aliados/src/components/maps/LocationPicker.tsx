'use client';

import { useEffect, useRef, useState } from 'react';
import { MapPin, LocateFixed } from 'lucide-react';
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

/** Mapa con marcador arrastrable — el aliado fija su ubicación exacta. */
export function LocationPicker({ lat, lng, onChange, height = 280, className = '' }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const markerRef = useRef<any>(null);
  const mapObjRef = useRef<any>(null);
  const [ready, setReady] = useState(false);

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
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function useMyLocation() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition((pos) => {
      const { latitude, longitude } = pos.coords;
      onChange(latitude, longitude);
      if (markerRef.current && mapObjRef.current) {
        const p = { lat: latitude, lng: longitude };
        markerRef.current.setPosition(p);
        mapObjRef.current.setCenter(p);
        mapObjRef.current.setZoom(16);
      }
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
    <div className={`relative rounded-xl overflow-hidden border border-border ${className}`}>
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
  );
}
