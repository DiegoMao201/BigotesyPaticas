import type { Metadata } from 'next';
import { PagoLibre } from './PagoLibre';

/**
 * Pagar sin pedido: abonos, saldos pendientes, cobros sueltos.
 *
 * Diego (5-oct-2026): *"necesito una de pagos libres que no lleven pedido"*. El caso
 * es el de siempre: "le quedé debiendo $30.000 de la peluquería", "quiero abonar a
 * la cuenta". Hasta hoy eso se cerraba en efectivo o por transferencia y había que
 * anotarlo a mano.
 *
 * Esta sí se indexa, al contrario que `/pagar/[referencia]`: aquella es el cobro de
 * una persona concreta; esta es una página de la tienda, igual de pública que el
 * catálogo, y sirve para enlazarla desde WhatsApp o la ficha de Google.
 */

export const metadata: Metadata = {
  title: 'Pagar o abonar en línea',
  description:
    'Paga o abona a tu cuenta de Bigotes y Paticas de forma segura: tarjeta, PSE, Nequi o Daviplata.',
  alternates: { canonical: 'https://bigotesypaticas.com/pagar' },
};

export default function PagarLibrePage() {
  return <PagoLibre />;
}
