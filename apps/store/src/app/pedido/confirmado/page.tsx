import type { Metadata } from 'next';
import { Suspense } from 'react';
import { EstadoDelPago } from './EstadoDelPago';

/**
 * A donde Bold devuelve al cliente cuando termina de pagar.
 *
 * LO QUE ESTA PAGINA **NO** HACE: creerle a la URL. Bold vuelve con
 * `?bold-order-id=X&bold-tx-status=approved`, y eso es texto que cualquiera puede
 * escribir a mano en la barra de direcciones. Si pintáramos "pago confirmado"
 * leyendo ese parámetro, bastaría con teclearlo para ver una pantalla de éxito de
 * un pedido que nadie pagó — y alguien podría usar la captura para reclamar.
 *
 * El parámetro sirve para UNA sola cosa: saber qué pedido preguntar. La respuesta
 * la da el servidor leyendo la base, donde el estado solo lo escriben el webhook
 * con firma válida o la conciliación.
 */

export const metadata: Metadata = {
  title: 'Tu pedido',
  description: 'Estado de tu pedido en Bigotes y Paticas.',
  // No tiene nada que hacer en Google: es una página privada de una compra.
  robots: { index: false, follow: false },
};

export default function ConfirmadoPage() {
  return (
    <div className="container-tight min-h-[70vh] py-16">
      <Suspense
        fallback={
          <p className="text-center text-sm text-muted-foreground">Cargando tu pedido…</p>
        }
      >
        <EstadoDelPago />
      </Suspense>
    </div>
  );
}
