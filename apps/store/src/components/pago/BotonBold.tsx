'use client';

/**
 * El botón de pago de Bold. Lo usan por igual el checkout, la página de pago por
 * enlace y —cuando se enganche— el portal de clientes.
 *
 * NADA DE LO QUE HAY AQUÍ SE CALCULA EN EL NAVEGADOR. El monto, la referencia y la
 * firma llegan tal cual los devolvió la API, que los sacó de los precios de la base
 * de datos. Este componente los pasa a Bold y ya. Si algún día alguien hiciera aquí
 * una cuenta —sumar el envío, aplicar un descuento—, la firma dejaría de cuadrar con
 * el monto y Bold rechazaría el cobro sin decir por qué.
 *
 * La llave que recibe es la de IDENTIDAD, que es pública por diseño y está hecha
 * para viajar al navegador. La secreta no sale del servidor en ningún caso.
 *
 * POR QUÉ EL BOTÓN SE MONTA CON DOM Y NO CON JSX
 * La librería de Bold no es un componente: es un `<script>` que lee sus propios
 * atributos `data-*` al ejecutarse y se sustituye por el botón. React no inserta
 * scripts escritos en JSX (los ignora por seguridad), así que hay que crear el
 * elemento a mano y colgarlo del DOM.
 */

import { useEffect, useRef, useState } from 'react';

const LIBRERIA = 'https://checkout.bold.co/library/boldPaymentButton.js';

export interface DatosBold {
  order_reference: string;
  amount: number;
  currency: string;
  integrity_signature: string;
  identity_key: string;
}

interface Props {
  datos: DatosBold;
  /** A dónde vuelve el cliente cuando Bold termina. */
  urlRetorno: string;
  descripcion?: string;
  /** Se avisa cuando el botón ya está puesto, para apagar el "preparando pago…". */
  onListo?: () => void;
}

export function BotonBold({ datos, urlRetorno, descripcion, onListo }: Props) {
  const caja = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const el = caja.current;
    if (!el) return;
    el.innerHTML = '';

    const script = document.createElement('script');
    script.src = LIBRERIA;
    script.setAttribute('data-bold-button', 'dark-L');
    script.setAttribute('data-api-key', datos.identity_key);
    // Entero, en texto. Bold espera "76000": ni "76.000" ni "76000.00".
    script.setAttribute('data-amount', String(datos.amount));
    script.setAttribute('data-currency', datos.currency || 'COP');
    script.setAttribute('data-order-id', datos.order_reference);
    script.setAttribute('data-integrity-signature', datos.integrity_signature);
    script.setAttribute('data-redirection-url', urlRetorno);
    script.setAttribute('data-render-mode', 'embedded');
    if (descripcion) script.setAttribute('data-description', descripcion.slice(0, 100));

    // Si la librería de Bold no carga —un bloqueador, una caída, un corte de red—,
    // el cliente no puede quedarse mirando un hueco: se le muestra la salida por
    // WhatsApp, que es la que ha funcionado siempre.
    script.onerror = () => setError(true);
    script.onload = () => onListo?.();

    el.appendChild(script);
    return () => {
      el.innerHTML = '';
    };
    // Se vuelve a montar solo si cambia el cobro. Remontarlo en cada render haría
    // parpadear el botón y, peor, podría abrir dos checkouts.
  }, [datos.order_reference, datos.amount, datos.integrity_signature, urlRetorno, descripcion, onListo, datos.identity_key, datos.currency]);

  if (error) {
    return (
      <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-semibold">No pudimos abrir el pago en línea.</p>
        <p className="mt-1">
          Puede ser tu conexión o un bloqueador de anuncios. Tu pedido ya quedó
          guardado: escríbenos por WhatsApp y lo cerramos contigo.
        </p>
        <a
          href="https://wa.me/573206876633"
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-block rounded-xl bg-green-600 px-4 py-2 font-semibold text-white"
        >
          Escribir por WhatsApp
        </a>
      </div>
    );
  }

  return <div ref={caja} className="min-h-[56px]" />;
}
