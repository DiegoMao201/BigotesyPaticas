import type { Metadata } from 'next';
import { PaginaDePago } from './PaginaDePago';

/**
 * La página de pago. **Un solo sitio donde se paga**, venga el cliente de donde
 * venga: del checkout de la tienda, del portal de clientes, o de un enlace que Diego
 * le mandó por WhatsApp. Esa es la razón de que el cobro viva en su propia página y
 * no dentro del checkout: un enlace se puede mandar, un paso de un formulario no.
 *
 * Lleva todo lo institucional —marca, dirección real, horario, la calificación de
 * Google— porque es la pantalla donde alguien decide si teclea su tarjeta. Lo que
 * genera confianza ahí no es decir "sitio seguro": es que se vea a quién le está
 * pagando, con la dirección del local y el teléfono de siempre.
 *
 * `noindex`: es el cobro de una persona concreta, no una página del catálogo.
 */

export const metadata: Metadata = {
  title: 'Pagar tu pedido',
  description: 'Paga tu pedido de Bigotes y Paticas de forma segura.',
  robots: { index: false, follow: false },
};

export default async function PagarPage({
  params,
}: {
  params: Promise<{ referencia: string }>;
}) {
  const { referencia } = await params;
  return <PaginaDePago referencia={referencia} />;
}
