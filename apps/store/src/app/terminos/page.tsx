import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Términos y Condiciones',
  description: 'Términos y condiciones de uso del sitio web y servicio de Bigotes y Paticas.',
  alternates: { canonical: 'https://bigotesypaticas.com/terminos' },
};

export default function TerminosPage() {
  return (
    <div className="container-tight py-16 max-w-3xl">
      <h1 className="text-3xl font-display font-bold mb-2">Términos y Condiciones</h1>
      <p className="text-muted-foreground text-sm mb-8">Última actualización: junio 2026</p>

      <div className="prose prose-sm max-w-none space-y-6 text-gray-700 leading-relaxed">
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
            Bigotes y Paticas es una tienda de productos para mascotas con entrega a domicilio en
            Pereira y Dosquebradas, Risaralda, Colombia. Operamos de lunes a sábado de 10:00 a 19:00.
            Los pedidos recibidos fuera de este horario son procesados al siguiente día hábil.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">3. Precios y disponibilidad</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Los precios están expresados en pesos colombianos (COP) e incluyen IVA cuando aplica</li>
            <li>Nos reservamos el derecho de modificar precios sin previo aviso</li>
            <li>La disponibilidad de productos está sujeta a existencias en inventario</li>
            <li>En caso de agotamiento de un producto pedido, le contactaremos para ofrecerle alternativas</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">4. Envío y entrega</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Envío gratis en pedidos desde $30.000 COP</li>
            <li>Costo de envío estándar: $8.000 COP</li>
            <li>Tiempo estimado: 1 a 3 días hábiles en Pereira y Dosquebradas</li>
            <li>Nos reservamos el derecho de rechazar pedidos con dirección fuera de nuestra zona de cobertura</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">5. Métodos de pago</h2>
          <p>
            Aceptamos efectivo contra entrega, tarjeta débito/crédito al recibir, Nequi, Daviplata
            y transferencia bancaria. El pago se realiza al momento de la entrega salvo indicación contraria.
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
            Bigotes y Paticas no se hace responsable por daños indirectos derivados del uso de los
            productos. Todos nuestros productos son distribuidos por marcas reconocidas con registro
            ICA o INVIMA vigente según corresponda.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">8. Ley aplicable</h2>
          <p>
            Estos términos se rigen por las leyes de la República de Colombia. Cualquier disputa
            será resuelta en los tribunales de Pereira, Risaralda.
          </p>
        </section>
      </div>

      <div className="mt-10 pt-6 border-t border-border flex gap-4 text-sm text-muted-foreground">
        <Link href="/politica-privacidad" className="hover:text-brand">Política de Privacidad</Link>
        <Link href="/devoluciones" className="hover:text-brand">Política de Devoluciones</Link>
        <Link href="/contacto" className="hover:text-brand">Contacto</Link>
      </div>
    </div>
  );
}
