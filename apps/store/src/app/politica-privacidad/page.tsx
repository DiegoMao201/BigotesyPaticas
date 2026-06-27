import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Política de Privacidad',
  description: 'Política de privacidad y tratamiento de datos personales de Bigotes y Paticas, conforme a la Ley 1581 de 2012.',
  alternates: { canonical: 'https://bigotesypaticas.com/politica-privacidad' },
};

export default function PoliticaPrivacidadPage() {
  return (
    <div className="container-tight py-16 max-w-3xl">
      <h1 className="text-3xl font-display font-bold mb-2">Política de Privacidad</h1>
      <p className="text-muted-foreground text-sm mb-8">Última actualización: junio 2026</p>

      <div className="prose prose-sm max-w-none space-y-6 text-gray-700 leading-relaxed">
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">1. Responsable del tratamiento</h2>
          <p>
            <strong>Diego Mauricio García</strong>, responsable del establecimiento comercial{' '}
            <strong>Bigotes y Paticas</strong>.<br />
            NIT: <strong>1088266407-7</strong> · Régimen Simple de Tributación.<br />
            Dirección: Mall Zamara Plaza, Cl. 15 #3A-07 Local 2, Dosquebradas, Risaralda, Colombia. C.P. 661001.<br />
            Contacto: <a href="mailto:bigotesypaticasdosquebradas@gmail.com" className="text-teal-600 hover:underline">
              bigotesypaticasdosquebradas@gmail.com
            </a> · +57 320 687 6633
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">2. Datos que recopilamos</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Nombre completo, número de identificación y teléfono (para procesar pedidos)</li>
            <li>Correo electrónico (para comunicaciones y notificaciones)</li>
            <li>Dirección de entrega (para domicilios)</li>
            <li>Información de mascotas (nombre, especie, raza) cuando se registra en el Portal</li>
            <li>Historial de compras y preferencias de productos</li>
            <li>Datos de navegación (cookies de análisis — ver sección 6)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">3. Finalidad del tratamiento</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Procesar y entregar pedidos</li>
            <li>Gestionar el programa de puntos y fidelización</li>
            <li>Enviar comunicaciones relacionadas con sus compras</li>
            <li>Con su consentimiento: enviar ofertas, novedades y tips de cuidado de mascotas</li>
            <li>Mejorar nuestros servicios mediante análisis estadísticos (datos anonimizados)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">4. Base legal (Ley 1581 de 2012)</h2>
          <p>
            El tratamiento de sus datos personales se realiza conforme a la Ley Estatutaria 1581 de 2012
            y el Decreto 1377 de 2013 de la República de Colombia. Usted puede ejercer sus derechos de
            conocer, actualizar, rectificar y suprimir sus datos escribiéndonos a nuestro correo.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">5. Tiempo de conservación</h2>
          <p>
            Conservamos sus datos mientras sea cliente activo y durante el período legal mínimo exigido
            (5 años para información contable y comercial). Tras ese periodo, los datos son eliminados
            de forma segura o anonimizados para fines estadísticos.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">6. Cookies y Google Analytics</h2>
          <p>
            Usamos Google Analytics 4 para analizar el tráfico de nuestro sitio de manera agregada y
            anónima. Los datos recopilados incluyen páginas visitadas, tiempo de navegación y
            dispositivo usado. No vendemos ni compartimos esta información con terceros.
            Puede desactivar las cookies en la configuración de su navegador.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">7. Sus derechos</h2>
          <p>Tiene derecho a:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Conocer, actualizar y rectificar sus datos personales</li>
            <li>Solicitar la supresión de sus datos (derecho al olvido)</li>
            <li>Revocar su consentimiento para comunicaciones comerciales</li>
            <li>Presentar quejas ante la Superintendencia de Industria y Comercio (SIC)</li>
          </ul>
          <p className="mt-3">
            Para ejercer sus derechos, escríbanos a{' '}
            <a href="mailto:bigotesypaticasdosquebradas@gmail.com" className="text-teal-600 hover:underline">
              bigotesypaticasdosquebradas@gmail.com
            </a>{' '}
            con el asunto &quot;Protección de datos&quot;. Respondemos en un máximo de 15 días hábiles.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">8. Cambios a esta política</h2>
          <p>
            Nos reservamos el derecho de actualizar esta política. Los cambios materiales serán
            notificados por email a los clientes registrados con al menos 15 días de anticipación.
          </p>
        </section>
      </div>

      <div className="mt-10 pt-6 border-t border-border flex gap-4 text-sm text-muted-foreground">
        <Link href="/terminos" className="hover:text-brand">Términos y Condiciones</Link>
        <Link href="/devoluciones" className="hover:text-brand">Política de Devoluciones</Link>
        <Link href="/contacto" className="hover:text-brand">Contacto</Link>
      </div>
    </div>
  );
}
