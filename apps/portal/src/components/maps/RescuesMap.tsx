'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { MapPin } from 'lucide-react';
import { loadMapsScript } from '@/lib/maps';
import type { RescueEvent } from '@/lib/api';

const KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? '';

interface Props {
  events: RescueEvent[];
  userLocation: { lat: number; lng: number } | null;
  height?: number;
  className?: string;
}

export function RescuesMap({ events, userLocation, height = 220, className = '' }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (!KEY || !mapRef.current || events.length === 0) return;
    const el = mapRef.current;

    loadMapsScript(KEY, () => {
      const center = userLocation ?? { lat: events[0].lat, lng: events[0].lng };
      const map = new window.google.maps.Map(el, {
        center,
        zoom: 12,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        zoomControl: true,
        styles: [{ featureType: 'poi', elementType: 'labels', stylers: [{ visibility: 'off' }] }],
      });

      if (userLocation) {
        new window.google.maps.Marker({
          position: userLocation,
          map,
          icon: {
            path: window.google.maps.SymbolPath.CIRCLE,
            scale: 7,
            fillColor: '#1a73e8',
            fillOpacity: 1,
            strokeColor: '#fff',
            strokeWeight: 2,
          },
          title: 'Tu ubicación',
        });
      }

      const bounds = new window.google.maps.LatLngBounds();
      if (userLocation) bounds.extend(userLocation);

      events.forEach((ev) => {
        const pos = { lat: ev.lat, lng: ev.lng };
        bounds.extend(pos);
        const marker = new window.google.maps.Marker({
          position: pos,
          map,
          title: ev.title,
          icon: {
            path: window.google.maps.SymbolPath.CIRCLE,
            scale: 10,
            fillColor: '#187f77',
            fillOpacity: 1,
            strokeColor: '#fff',
            strokeWeight: 2,
          },
          label: { text: String(ev.animal_count), color: '#fff', fontSize: '11px', fontWeight: '700' },
        });
        const info = new window.google.maps.InfoWindow({
          content: `<div style="font-family:system-ui,sans-serif;padding:2px;min-width:150px">
            <p style="font-weight:700;font-size:13px;margin:0 0 2px">${ev.title}</p>
            <p style="font-size:11px;color:#666;margin:0">${ev.animal_count} animalito${ev.animal_count === 1 ? '' : 's'} · ${ev.address ?? ''}</p>
          </div>`,
        });
        marker.addListener('click', () => info.open(map, marker));
        marker.addListener('dblclick', () => router.push(`/sos/encontrados/${ev.id}`));
      });

      if (events.length > 1 || userLocation) map.fitBounds(bounds, 48);
      else map.setCenter(center);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [events.length, userLocation?.lat, userLocation?.lng]);

  if (!KEY || events.length === 0) return null;

  return (
    <div className={`rounded-2xl overflow-hidden border border-white/80 shadow-sm ${className}`}>
      <div ref={mapRef} style={{ width: '100%', height }} />
      <div className="bg-white px-3 py-1.5 flex items-center gap-1.5 text-[11px] text-muted">
        <MapPin className="h-3 w-3" /> Toca un punto para ver dónde se encontraron
      </div>
    </div>
  );
}
