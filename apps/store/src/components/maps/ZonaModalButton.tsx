'use client';

import { useEffect, useState } from 'react';
import { MapPin, X } from 'lucide-react';
import { DeliveryZoneChecker } from './DeliveryZoneChecker';

/**
 * "¿Llegamos a tu zona?" en la ficha de producto.
 *
 * Diego (19-sep-2026): "esas tarjetas en la ficha del producto deben ser de clic
 * y pum le sale mi mapa para que la gente sepa si le entregamos en su dirección".
 * El comprobador ya existía (DeliveryZoneChecker, con Distance Matrix) pero solo
 * vivía en /contacto, donde nadie llega con un producto en la mano. Aquí se abre
 * en un modal encima de la ficha, sin sacar al cliente de la compra.
 *
 * El script de Maps se carga solo cuando se abre el modal (lo hace el propio
 * DeliveryZoneChecker), así la ficha no paga ese peso si nadie pregunta.
 */
export function ZonaModalButton() {
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    if (!abierto) return;
    const cerrar = (e: KeyboardEvent) => e.key === 'Escape' && setAbierto(false);
    window.addEventListener('keydown', cerrar);
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', cerrar);
      document.body.style.overflow = '';
    };
  }, [abierto]);

  return (
    <>
      <button
        type="button"
        onClick={() => setAbierto(true)}
        className="flex items-center justify-center gap-2.5 w-full py-3 rounded-2xl border-2 border-teal-500 text-teal-700 font-semibold hover:bg-teal-50 transition-colors text-sm"
      >
        <MapPin className="h-4 w-4" />
        ¿Llegamos a tu zona? Compruébalo aquí
      </button>

      {abierto && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 p-0 sm:p-4"
          onClick={() => setAbierto(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Comprobar zona de domicilio"
        >
          <div
            className="w-full sm:max-w-lg bg-white rounded-t-3xl sm:rounded-3xl shadow-2xl max-h-[92vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 pt-4 pb-2">
              <h2 className="font-display font-bold text-lg text-[#0d4a45]">¿Llegamos a tu dirección?</h2>
              <button
                type="button"
                onClick={() => setAbierto(false)}
                aria-label="Cerrar"
                className="p-2 rounded-full hover:bg-gray-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="px-5 pb-6">
              <DeliveryZoneChecker />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
