'use client';

import { useEffect, useRef } from 'react';
import { MapPin } from 'lucide-react';
import { BUSINESS_INFO } from '@/lib/business-info';
import { loadMapsScript } from '@/lib/maps';

const KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? '';
const GOOGLE_MAPS_URL =
  'https://www.google.com/maps/search/?api=1&query=Bigotes+y+Paticas+Mall+Zamara+Plaza+Dosquebradas';

interface Props {
  height?: number;
  zoom?: number;
  className?: string;
}

export function StoreMapEmbed({ height = 420, zoom = 17, className = '' }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!KEY || !mapRef.current) return;
    const el = mapRef.current;

    loadMapsScript(KEY, () => {
      const center = { lat: BUSINESS_INFO.geo.latitude, lng: BUSINESS_INFO.geo.longitude };

      const map = new window.google.maps.Map(el, {
        center,
        zoom,
        mapTypeControl: false,
        streetViewControl: true,
        fullscreenControl: true,
        zoomControl: true,
        styles: [
          { featureType: 'poi', elementType: 'labels', stylers: [{ visibility: 'off' }] },
        ],
      });

      const marker = new window.google.maps.Marker({
        position: center,
        map,
        title: BUSINESS_INFO.name,
        animation: window.google.maps.Animation.DROP,
      });

      const info = new window.google.maps.InfoWindow({
        content: `<div style="font-family:system-ui,sans-serif;padding:4px 2px;max-width:220px;">
          <p style="font-weight:700;font-size:14px;margin:0 0 4px">${BUSINESS_INFO.name}</p>
          <p style="font-size:12px;color:#555;margin:0 0 2px">Mall Zamara Plaza, Cl. 15 #3A-07 Local 2</p>
          <p style="font-size:12px;color:#555;margin:0 0 8px">Dosquebradas, Risaralda</p>
          <a href="${GOOGLE_MAPS_URL}" target="_blank"
            style="font-size:12px;color:#0a7f6c;font-weight:600;text-decoration:none">
            📍 Cómo llegar →
          </a>
        </div>`,
      });

      info.open(map, marker);
      marker.addListener('click', () => info.open(map, marker));
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!KEY) {
    return (
      <div
        className={`rounded-2xl overflow-hidden border border-border shadow-sm flex items-center justify-center bg-gray-50 ${className}`}
        style={{ height }}
      >
        <div className="text-center space-y-2 text-muted-foreground">
          <MapPin className="h-8 w-8 mx-auto text-brand-400" />
          <p className="text-sm font-medium">Mall Zamara Plaza, Cl. 15 #3A-07 Local 2</p>
          <p className="text-xs">Dosquebradas, Risaralda</p>
          <a
            href={GOOGLE_MAPS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block text-xs text-brand-600 font-semibold hover:underline"
          >
            Ver en Google Maps →
          </a>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`rounded-2xl overflow-hidden border border-border shadow-sm ${className}`}
    >
      <div ref={mapRef} style={{ width: '100%', height }} />
    </div>
  );
}
