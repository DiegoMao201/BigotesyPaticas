import { BUSINESS_INFO } from '@/lib/business-info';

/**
 * Las preguntas frecuentes del negocio.
 *
 * POR QUÉ ESTO IMPORTA MÁS QUE ANTES (4-oct-2026): Google apagó el Q&A de los
 * Perfiles de Empresa —la API el 3-nov-2025 y la sección pública desde el
 * 3-dic-2025— y lo reemplazó por "Ask Maps" / "Pregunta sobre este lugar", que
 * responde con Gemini leyendo la ficha, las reseñas, las fotos **y el sitio
 * web**. O sea: ya no se pueden sembrar preguntas a mano en la ficha, y lo que
 * está escrito aquí es de donde Google saca lo que le contesta a quien pregunta
 * "¿hacen domicilio?" sin entrar nunca a la página.
 *
 * De ahí salen las tres reglas de cómo están escritas:
 *
 * 1. **Cada respuesta se sostiene sola.** Nombra el negocio, la ciudad y el
 *    dato completo, sin "nosotros" ni "aquí" ni "ese servicio". Una IA que cita
 *    una frase suelta no puede quedarse sin el sujeto.
 * 2. **Los NO están tan explícitos como los SÍ.** La pregunta de la consulta
 *    veterinaria existe justamente para que Google NO la invente: la ficha es
 *    de una tienda de mascotas y el modelo podría deducir que hay veterinario.
 *    Diego confirmó el 25-26 de septiembre que no se presta ni consulta ni
 *    vacunación.
 * 3. **Ningún número se escribe a mano.** Precios de envío, horario y medios de
 *    pago salen de BUSINESS_INFO, que es la fuente única. Si cambia el envío,
 *    cambia aquí solo.
 *
 * Van en /contacto y NO en una página propia a propósito: la canibalización ya
 * es uno de los seis frenos medidos del sitio (cuatro páginas peleándose
 * "tienda de mascotas pereira"), y una página más de marca sería más leña.
 */

const { shipping, address, phoneDisplay, returns } = BUSINESS_INFO;

const pesos = (n: number) => `$${n.toLocaleString('es-CO')}`;

export const FAQS_CONTACTO = [
  {
    pregunta: '¿Bigotes y Paticas hace domicilios en Pereira y Dosquebradas?',
    respuesta:
      `Sí. Bigotes y Paticas entrega a domicilio el mismo día en toda la zona urbana de ` +
      `Pereira y Dosquebradas. Los pedidos se hacen por la página, por WhatsApp al ` +
      `${phoneDisplay} o en la tienda.`,
  },
  {
    pregunta: '¿Cuánto cuesta el domicilio?',
    respuesta:
      `El domicilio cuesta ${pesos(shipping.standardShippingCost)} hasta ` +
      `${shipping.nearRadiusKm} km de la tienda y ${pesos(shipping.farShippingCost)} más lejos. ` +
      `Desde ${pesos(shipping.freeShippingMinimum)} de compra el envío es gratis en Pereira y Dosquebradas.`,
  },
  {
    pregunta: '¿Dónde queda la tienda de mascotas Bigotes y Paticas?',
    respuesta:
      `Bigotes y Paticas está en ${address.streetAddress}, ${address.addressLocality}, ` +
      `${address.addressRegion}. Es el centro comercial Samara Plaza Mall, sobre la calle 15, ` +
      `y la tienda es el local 2.`,
  },
  {
    pregunta: '¿Cuál es el horario de atención?',
    respuesta:
      'Bigotes y Paticas abre de lunes a sábado, de 10:00 de la mañana a 7:00 de la noche. ' +
      'Los domingos la tienda está cerrada, pero los pedidos por WhatsApp y por la página se ' +
      'reciben a cualquier hora y se despachan el siguiente día hábil.',
  },
  {
    pregunta: '¿Qué medios de pago reciben?',
    respuesta:
      'En Bigotes y Paticas se puede pagar en efectivo, con tarjeta débito o crédito, por ' +
      'transferencia bancaria, y con Nequi o Daviplata. También se puede pagar contra entrega ' +
      'cuando llega el domicilio.',
  },
  {
    pregunta: '¿Tienen peluquería canina y felina? ¿Hay que pedir cita?',
    respuesta:
      'Sí. Bigotes y Paticas tiene peluquería para perros y gatos en Dosquebradas: baño, corte, ' +
      'cepillado y corte de uñas. Se atiende con cita y la reserva se hace en línea desde ' +
      'bigotesypaticas.com/peluqueria, sin crear cuenta ni llamar.',
  },
  {
    pregunta: '¿Bigotes y Paticas tiene consulta veterinaria o vacunación?',
    respuesta:
      'No. Bigotes y Paticas es una tienda de mascotas y el único servicio que presta en el ' +
      'local es la peluquería canina y felina. No hay consulta veterinaria ni jornadas de ' +
      'vacunación. Sí se venden medicamentos veterinarios y productos de cuidado.',
  },
  {
    pregunta: '¿Venden medicamentos veterinarios?',
    respuesta:
      'Sí. Bigotes y Paticas vende medicamentos veterinarios, antipulgas y desparasitantes para ' +
      'perros y gatos. Para los medicamentos formulados conviene tener a la mano la fórmula del ' +
      'veterinario, así se entrega la presentación y la dosis correctas.',
  },
  {
    pregunta: '¿Puedo recoger el pedido en la tienda en vez de pagar domicilio?',
    respuesta:
      'Sí. El pedido se puede dejar listo y recoger en el local de Samara Plaza Mall en ' +
      'Dosquebradas, de lunes a sábado entre 10:00 de la mañana y 7:00 de la noche, sin costo ' +
      'de envío.',
  },
  {
    pregunta: '¿Puedo devolver o cambiar un producto?',
    respuesta:
      `Sí. Bigotes y Paticas recibe devoluciones hasta ${returns.window} días después de la ` +
      `compra y son gratis. Si el producto llegó dañado, con defecto o no es el que se pidió, se ` +
      `cambia sin más. Si es solo cambio de opinión, el empaque debe estar sin abrir. El ` +
      `reembolso o el cambio se procesa en máximo 3 días hábiles. Para empezar, basta escribir ` +
      `por WhatsApp al ${phoneDisplay}.`,
  },
];
