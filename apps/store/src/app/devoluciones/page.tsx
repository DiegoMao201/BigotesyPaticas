import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Política de Devoluciones',
  description: 'Política de devoluciones y cambios de Bigotes y Paticas. 30 días, gratis, sin complicaciones.',
};

export default function DevolucionesPage() {
  return (
    <div className="container-tight py-16 max-w-3xl">
      <h1 className="text-3xl font-display font-bold mb-2">Política de Devoluciones</h1>
      <p className="text-muted-foreground text-sm mb-8">Última actualización: junio 2026</p>

      <div className="bg-teal-50 border border-teal-200 rounded-2xl p-6 mb-8">
        <p className="text-teal-800 font-semibold text-lg">↩️ 30 días · Devoluciones gratis · Sin preguntas</p>
        <p className="text-teal-700 text-sm mt-1">Tu satisfacción y la de tu mascota son nuestra prioridad.</p>
      </div>

      <div className="prose prose-sm max-w-none space-y-6 text-gray-700 leading-relaxed">
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">¿Cuándo puedes devolver?</h2>
          <ul className="list-disc pl-5 space-y-2">
            <li>El producto llegó dañado o en mal estado</li>
            <li>Recibiste un producto diferente al que pediste</li>
            <li>El producto tiene defecto de fabricación</li>
            <li>Simplemente cambiaste de opinión (dentro de 30 días, sin abrir el empaque)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Productos que NO aplican para devolución</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Alimentos abiertos o con empaque roto (por razones sanitarias)</li>
            <li>Medicamentos veterinarios una vez iniciado el tratamiento</li>
            <li>Productos personalizados o hechos a medida</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">¿Cómo solicitar una devolución?</h2>
          <ol className="list-decimal pl-5 space-y-2">
            <li>
              Escríbenos por WhatsApp al{' '}
              <a href="https://wa.me/573206876633" target="_blank" rel="noopener noreferrer" className="text-teal-600 hover:underline">
                +57 320 687 6633
              </a>{' '}
              o al correo{' '}
              <a href="mailto:bigotesypaticasdosquebradas@gmail.com" className="text-teal-600 hover:underline">
                bigotesypaticasdosquebradas@gmail.com
              </a>
            </li>
            <li>Cuéntanos el motivo de la devolución y adjunta una foto del producto</li>
            <li>
              Acordaremos el método de devolución: puedes traer el producto a nuestra tienda en
              <strong> Mall Zamara Plaza, Cl. 15 #3A-07 Local 2, Dosquebradas</strong>, o coordinamos
              un reenvío gratuito.
            </li>
            <li>Una vez recibido el producto, procesamos el reembolso o cambio en máximo 3 días hábiles.</li>
          </ol>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Métodos de reembolso</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Transferencia bancaria o Nequi/Daviplata al mismo medio de pago original</li>
            <li>Crédito en Puntos Bigotes (opcional, con bono del 5% adicional)</li>
            <li>Cambio por otro producto de igual o mayor valor</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Plazo de respuesta</h2>
          <p>
            Respondemos todas las solicitudes de devolución en máximo <strong>24 horas hábiles</strong>.
            Nuestro horario de atención es lunes a sábado de 10:00 a 19:00.
          </p>
        </section>
      </div>

      <div className="mt-10 pt-6 border-t border-border flex gap-4 text-sm text-muted-foreground">
        <Link href="/terminos" className="hover:text-brand">Términos y Condiciones</Link>
        <Link href="/politica-privacidad" className="hover:text-brand">Política de Privacidad</Link>
        <Link href="/contacto" className="hover:text-brand">Contacto</Link>
      </div>
    </div>
  );
}
