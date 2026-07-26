'use client';

import { useCallback, useState } from 'react';

export interface Coords {
  lat: number;
  lng: number;
}

export function useGeolocation() {
  const [coords, setCoords] = useState<Coords | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const getCurrentPosition = useCallback((): Promise<Coords> => {
    return new Promise((resolve, reject) => {
      if (typeof window === 'undefined' || !navigator.geolocation) {
        const msg = 'Tu navegador no soporta geolocalización';
        setError(msg);
        reject(new Error(msg));
        return;
      }
      setLoading(true);
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const next = { lat: pos.coords.latitude, lng: pos.coords.longitude };
          setCoords(next);
          setError(null);
          setLoading(false);
          resolve(next);
        },
        (err) => {
          const msg =
            err.code === err.PERMISSION_DENIED
              ? 'Necesitamos tu ubicación para mostrarte reportes cerca de ti'
              : 'No pudimos obtener tu ubicación. Intenta de nuevo.';
          setError(msg);
          setLoading(false);
          reject(new Error(msg));
        },
        { enableHighAccuracy: true, timeout: 10_000, maximumAge: 60_000 }
      );
    });
  }, []);

  return { coords, error, loading, getCurrentPosition };
}
