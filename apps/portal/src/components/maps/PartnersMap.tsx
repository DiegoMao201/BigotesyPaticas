'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { MapPin } from 'lucide-react';
import { loadMapsScript } from '@/lib/maps';
import type { Partner } from '@/lib/api';

const KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? '';

const TYPE_COLOR: Record<string, string> = {
  vet: '#187f77',
  walker: '#f5a641',
  shelter: '#0d4a45',
  groomer: '#e05252',
};

interface Props {
  partners: Partner[];
  userLocation: { lat: number; lng: number } | null;
  height?: number;
  className?: string;
}

export function PartnersMap({ partners, userLocation, height = 220, className = '' }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const withLocation = partners.filter((p) => p.lat != null && p.lng != null);

  useEffect(() => {
    if (!KEY || !mapRef.current || withLocation.length === 0) return;
    const el = mapRef.current;

    loadMapsScript(KEY, () => {
      const center = userLocation ?? { lat: withLocation[0].lat as number, lng: withLocation[0].lng as number };
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

      withLocation.forEach((p) => {
        const pos = { lat: p.lat as number, lng: p.lng as number };
        bounds.extend(pos);
        const marker = new window.google.maps.Marker({
          position: pos,
          map,
          title: p.business_name,
          icon: {
            path: window.google.maps.SymbolPath.CIRCLE,
            scale: 9,
            fillColor: TYPE_COLOR[p.partner_type] ?? '#187f77',
            fillOpacity: 1,
            strokeColor: '#fff',
            strokeWeight: 2,
          },
        });
        const info = new window.google.maps.InfoWindow({
          content: `<div style="font-family:system-ui,sans-serif;padding:2px;min-width:140px">
            <p style="font-weight:700;font-size:13px;margin:0 0 2px">${p.business_name}</p>
            <p style="font-size:11px;color:#666;margin:0">${p.city}</p>
          </div>`,
        });
        marker.addListener('click', () => {
          info.open(map, marker);
        });
        marker.addListener('dblclick', () => router.push(`/servicios/${p.slug}`));
      });

      if (withLocation.length > 1 || userLocation) map.fitBounds(bounds, 48);
      else map.setCenter(center);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [partners.length, userLocation?.lat, userLocation?.lng]);

  if (!KEY || withLocation.length === 0) return null;

  return (
    <div className={`rounded-2xl overflow-hidden border border-white/80 shadow-sm ${className}`}>
      <div ref={mapRef} style={{ width: '100%', height }} />
      <div className="bg-white px-3 py-1.5 flex items-center gap-1.5 text-[11px] text-muted">
        <MapPin className="h-3 w-3" /> Toca un punto para ver el aliado
      </div>
    </div>
  );
}
