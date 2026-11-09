import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Términos y Condiciones',
  description: 'Términos y condiciones de uso del sitio web y servicio de Bigotes y Paticas.',
  alternates: { canonical: 'https://bigotesypaticas.com/terminos' },
  openGraph: { url: 'https://bigotesypaticas.com/terminos' },
};

export default function TerminosPage() {
  return (
    <div className="container-tight py-16 max-w-3xl">
      <h1 className="text-3xl font-display font-bold mb-2">Términos y Condiciones</h1>
      <p className="text-muted-foreground text-sm mb-8">Última actualización: 8 de noviembre de 2026</p>

      <div className="prose prose-sm max-w-none space-y-6 text-gray-700 leading-relaxed">
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Quién vende</h2>
          <p>
            <strong>Diego Mauricio García Rengifo</strong>, persona natural, NIT 1088266407-7, propietario del establecimiento
            de comercio <strong>Bigotes y Paticas</strong> (matrícula mercantil 68875, Cámara de Comercio de Dosquebradas).
            Dirección para notificaciones: Cl. 15 #3A-07, C.C. Samara Plaza, Local 2, Dosquebradas, Risaralda, Colombia.
            Correo: bigotesypaticasdosquebradas@gmail.com · WhatsApp +57 320 687 6633. Estos términos aplican a la web,
            al portal mi.bigotesypaticas.com y a la app Bigotes y Paticas.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">1. Aceptación</h2>
          <p>
            Al acceder y usar bigotesypaticas.com y nuestros servicios, usted acepta estos términos.
            Si no está de acuerdo, por favor no use el sitio.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">2. Servicio</h2>
          <p>
            Bigotes y Paticas es una tienda de productos para mascotas con entrega a domicilio propio en
            Pereira y Dosquebradas, Risaralda, y envíos al resto de Colombia por transportadora.
            Operamos de lunes a sábado de 10:00 a 19:00.
            Los pedidos recibidos fuera de este horario son procesados al siguiente día hábil.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">3. Precios y disponibilidad</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Los precios publicados son precios finales en pesos colombianos (COP). Bigotes y Paticas no es responsable de IVA, por lo que no se suma IVA al precio</li>
            <li>Los precios pueden cambiar, pero el precio que pagas es el que se mostró al confirmar tu pedido</li>
            <li>La disponibilidad de productos está sujeta a existencias en inventario</li>
            <li>En caso de agotamiento de un producto pedido, le contactaremos para ofrecerle alternativas</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">4. Envío y entrega</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Envío gratis en pedidos desde $30.000 COP</li>
            <li>Pedidos de menos de $30.000: domicilio de $3.000 COP hasta 5 km del local y de $5.000 COP a mayor distancia</li>
            <li>Pedidos hechos desde el portal de clientes (mi.bigotesypaticas.com): domicilio gratis</li>
            <li>Tiempo estimado: 1 a 3 días hábiles en Pereira y Dosquebradas</li>
            <li>
              Envíos a otras ciudades de Colombia: por transportadora (Coordinadora, Servientrega, Inter
              Rapidísimo o TCC). El valor del envío se cotiza en el checkout según la ciudad y el peso del
              pedido, se muestra antes de pagar y se cobra junto con los productos
            </li>
            <li>
              Los envíos nacionales se pagan en línea antes del despacho; fuera de Pereira y Dosquebradas
              no hay pago contra entrega
            </li>
            <li>
              Tiempo estimado de los envíos nacionales: el que indica la transportadora al cotizar
              (días hábiles contados desde que recibe el paquete). Al generar la guía, el cliente recibe
              el número para rastrear su paquete
            </li>
            <li>
              Responsabilidades en envíos nacionales: la compra se celebra con Bigotes y Paticas, que
              responde por el producto, su estado y su empaque. El transporte lo presta la
              transportadora elegida por el cliente, contratada a través de Envia.com, que responde por
              el paquete mientras está en su poder y define los tiempos de entrega. Ante un retraso,
              daño o pérdida en tránsito, Bigotes y Paticas presenta y gestiona la reclamación ante la
              transportadora en nombre del cliente
            </li>
            <li>Nos reservamos el derecho de rechazar pedidos con dirección que ninguna transportadora cubra</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">5. Métodos de pago</h2>
          <p>
            Aceptamos efectivo contra entrega, tarjeta débito/crédito al recibir, Nequi, Daviplata
            y transferencia bancaria, y pago en línea (tarjeta, PSE, Nequi y Daviplata) a través de Bold.
            En Pereira y Dosquebradas el pago puede hacerse al momento de la entrega; los envíos a otras
            ciudades se pagan siempre en línea.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">6. Programa de puntos</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Ganas 1 Punto Bigotes por cada $1.000 COP en compras</li>
            <li>Al registrarte: 50 puntos de bienvenida</li>
            <li>Por referidos: 100 puntos cuando tu referido hace su primera compra</li>
            <li>Los puntos no tienen valor en efectivo y son intransferibles</li>
            <li>Nos reservamos el derecho de modificar o cancelar el programa con 30 días de aviso</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">7. Limitación de responsabilidad</h2>
          <p>
            Sin perjuicio de la garantía legal y de los derechos que te da la Ley 1480 de 2011, Bigotes y
            Paticas no responde por daños derivados del uso indebido de los productos o contrario a sus
            instrucciones. Todos nuestros productos son distribuidos por marcas reconocidas con registro
            ICA o INVIMA vigente según corresponda.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">8. Tus derechos como consumidor</h2>
          <p>
            Tienes derecho de <strong>retracto</strong> (5 días hábiles desde la entrega), a la <strong>reversión del pago</strong>{' '}
            en compras en línea y a la <strong>garantía legal</strong>, según la Ley 1480 de 2011 (Estatuto del Consumidor).
            Cómo ejercerlos está en la <Link href="/devoluciones" className="text-teal-600 hover:underline">política de devoluciones y retracto</Link>.
            La autoridad de protección al consumidor es la Superintendencia de Industria y Comercio (www.sic.gov.co).
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">9. Ley aplicable</h2>
          <p>
            Estos términos se rigen por las leyes de la República de Colombia. Cualquier disputa
            será resuelta en los tribunales de Pereira, Risaralda.
          </p>
        </section>
      </div>

      <div className="mt-10 pt-6 border-t border-border flex gap-4 text-sm text-muted-foreground">
        <Link href="/politica-privacidad" className="hover:text-brand">Política de Privacidad</Link>
        <Link href="/devoluciones" className="hover:text-brand">Devoluciones y retracto</Link>
        <Link href="/contacto" className="hover:text-brand">Contacto</Link>
      </div>
    </div>
  );
}
