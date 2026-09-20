'use client';

import { useEffect, useRef, useState } from 'react';
import { loadMapsScript } from '@/lib/maps';

const MAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? '';

/**
 * Campo de dirección con autocompletado de Google (Places Autocomplete).
 *
 * Diego (19-sep-2026) vio la "herramienta de creación rápida" de Google Maps
 * Platform: autocompletar direcciones en el formulario para que la gente no se
 * equivoque al escribirla. Es lo mismo que ya hace DeliveryZoneChecker, pero el
 * checkout tenía un input plano. Aquí se reutiliza el mismo cargador y los
 * mismos límites (Pereira–Dosquebradas, solo Colombia).
 *
 * DOS GARANTÍAS, porque el checkout es donde se cierra la venta:
 *  1. El script de Maps se carga SOLO cuando la persona toca el campo. Quien
 *     nunca lo toca no descarga nada.
 *  2. Si no hay clave, o el script no carga, o Google devuelve error, el campo
 *     sigue siendo un input de texto normal. Nunca bloquea el pedido.
 *
 * Y una aclaración que conviene dejar escrita: esto mejora la conversión del
 * pedido (menos errores de dirección), NO el posicionamiento en Maps. Google no
 * premia a quien usa su API.
 */
type Props = {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
  id?: string;
};

export function AddressAutocompleteInput({ value, onChange, placeholder, className, id }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [armado, setArmado] = useState(false);

  useEffect(() => {
    if (!armado || !MAPS_KEY || !inputRef.current) return;
    try {
      loadMapsScript(MAPS_KEY, () => {
        if (!inputRef.current || !window.google?.maps?.places) return;
        const ac = new window.google.maps.places.Autocomplete(inputRef.current, {
          bounds: new window.google.maps.LatLngBounds(
            new window.google.maps.LatLng(4.65, -75.85),
            new window.google.maps.LatLng(4.97, -75.55),
          ),
          componentRestrictions: { country: 'co' },
          fields: ['formatted_address', 'name'],
        });
        ac.addListener('place_changed', () => {
          const place = ac.getPlace();
          const texto = place?.formatted_address ?? place?.name;
          if (texto) onChange(texto);
        });
      });
    } catch {
      // sin autocompletado: el input sigue siendo un input
    }
  }, [armado, onChange]);

  return (
    <input
      ref={inputRef}
      id={id}
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onFocus={() => setArmado(true)}
      placeholder={placeholder}
      className={className}
      autoComplete="street-address"
    />
  );
}
