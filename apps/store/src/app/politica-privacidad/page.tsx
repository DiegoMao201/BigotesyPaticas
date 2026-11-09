import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Política de Privacidad',
  description: 'Política de tratamiento de datos personales de Bigotes y Paticas (web y app), conforme a la Ley 1581 de 2012.',
  alternates: { canonical: 'https://bigotesypaticas.com/politica-privacidad' },
};

const H2 = ({ children }: { children: React.ReactNode }) => (
  <h2 className="text-xl font-bold text-gray-900 mb-3">{children}</h2>
);
const correo = (
  <a href="mailto:bigotesypaticasdosquebradas@gmail.com" className="text-teal-600 hover:underline">
    bigotesypaticasdosquebradas@gmail.com
  </a>
);

/** Versión 2 (8-nov-2026): cubre la app de Android, la ubicación, la huella, Google, Bold y la eliminación de cuenta. */
export default function PoliticaPrivacidadPage() {
  return (
    <div className="container-tight py-16 max-w-3xl">
      <h1 className="text-3xl font-display font-bold mb-2">Política de Tratamiento de Datos Personales</h1>
      <p className="text-muted-foreground text-sm mb-8">Versión 2 · vigente desde el 8 de noviembre de 2026 · aplica a bigotesypaticas.com, mi.bigotesypaticas.com y la app Bigotes y Paticas</p>

      <div className="prose prose-sm max-w-none space-y-6 text-gray-700 leading-relaxed">
        <section>
          <H2>1. Responsable del tratamiento</H2>
          <p>
            <strong>Diego Mauricio García Rengifo</strong>, persona natural, C.C. 1088266407, NIT <strong>1088266407-7</strong>,
            propietario del establecimiento de comercio <strong>Bigotes y Paticas</strong> (matrícula mercantil 68875,
            Cámara de Comercio de Dosquebradas). Régimen ordinario, no responsable de IVA.<br />
            Dirección: Cl. 15 #3A-07, C.C. Samara Plaza, Local 2, Dosquebradas, Risaralda, Colombia.<br />
            Contacto: {correo} · WhatsApp +57 320 687 6633 · lunes a sábado de 10:00 a 19:00.
          </p>
        </section>

        <section>
          <H2>2. Qué datos recogemos y para qué</H2>
          <ul className="list-disc pl-5 space-y-2">
            <li><strong>Cédula, nombre, teléfono, correo y dirección:</strong> identificarte, entregar tus pedidos, facturar y atenderte.</li>
            <li><strong>Datos de tus mascotas</strong> (nombre, especie, raza, fotos, vacunas e historial): carnet digital, recordatorios y citas de peluquería.</li>
            <li><strong>Pedidos, pagos, puntos y reseñas:</strong> procesar compras, el programa de puntos y mejorar el servicio.</li>
            <li><strong>Ubicación aproximada, solo si la autorizas:</strong> avisarte de mascotas perdidas cerca de ti. Se pide con la app abierta, nunca en segundo plano, y nunca se muestra a otros clientes. Puedes quitar el permiso cuando quieras desde tu celular.</li>
            <li><strong>Cuenta de Google</strong> (nombre, correo e identificador), si eliges entrar con Google: iniciar sesión.</li>
            <li><strong>Huella o Face ID (llave de acceso):</strong> iniciar sesión. Tu huella o tu cara <strong>nunca salen de tu celular</strong>; solo guardamos una llave pública que no permite reconstruirlas.</li>
            <li><strong>Publicaciones de mascotas perdidas o en adopción:</strong> lo que tú publiques lo verán otros usuarios.</li>
            <li><strong>Datos de uso</strong> (páginas vistas, dispositivo, cookies): medir la web y la app con Google Analytics (en la web) y el píxel de Meta (en la web y en la app), para saber qué funciona y medir nuestra publicidad.</li>
          </ul>
          <p className="mt-3">
            <strong>No pedimos ni guardamos los datos de tu tarjeta.</strong> Los pagos en línea los procesa Bold; nosotros solo recibimos la confirmación del pago.
            No tratamos datos sensibles ni datos de menores de edad: la app es para mayores de 18 años.
          </p>
        </section>

        <section>
          <H2>3. Con quién compartimos datos</H2>
          <p>Solo con quienes nos ayudan a prestar el servicio (encargados), y únicamente lo necesario:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li><strong>Bold</strong> — pagos en línea (Colombia).</li>
            <li><strong>Hetzner</strong> (Alemania) — servidores donde vive la base de datos.</li>
            <li><strong>DigitalOcean</strong> (Estados Unidos) — almacenamiento de imágenes.</li>
            <li><strong>Cloudflare</strong> — entrega segura y rápida de la web.</li>
            <li><strong>Google</strong> — inicio de sesión con Google, analítica de la web y envío de correos.</li>
            <li><strong>Meta</strong> — medición de publicidad (píxel) y atención por WhatsApp.</li>
            <li><strong>Transportadoras</strong> — solo para envíos fuera de Pereira y Dosquebradas.</li>
            <li>Autoridades, cuando la ley lo exija.</li>
          </ul>
          <p className="mt-3">
            Algunos de estos proveedores están fuera de Colombia, por lo que tus datos pueden almacenarse en el exterior
            (transferencia o transmisión internacional). Al aceptar esta política lo autorizas, y exigimos a esos proveedores
            medidas de seguridad adecuadas. <strong>No vendemos ni alquilamos tus datos.</strong>
          </p>
        </section>

        <section>
          <H2>4. Tus derechos (Ley 1581 de 2012 y Decreto 1377 de 2013)</H2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Conocer, actualizar y rectificar tus datos.</li>
            <li>Pedir prueba de la autorización que nos diste.</li>
            <li>Saber cómo hemos usado tus datos.</li>
            <li>Revocar la autorización y pedir que borremos tus datos, cuando no exista un deber legal de conservarlos.</li>
            <li>Presentar quejas ante la Superintendencia de Industria y Comercio (SIC), después de haber acudido a nosotros.</li>
            <li>Acceder gratis a tus datos.</li>
          </ul>
          <p className="mt-3">
            Escríbenos a {correo} con el asunto &quot;Protección de datos&quot; o por WhatsApp. Las <strong>consultas</strong> se responden
            en máximo 10 días hábiles y los <strong>reclamos</strong> en máximo 15 días hábiles, como manda la ley.
          </p>
        </section>

        <section>
          <H2>5. Eliminar tu cuenta</H2>
          <p>
            Desde la app (<strong>Perfil → Eliminar mi cuenta</strong>) o en{' '}
            <Link href="/eliminar-cuenta" className="text-teal-600 hover:underline">bigotesypaticas.com/eliminar-cuenta</Link>.
            La cuenta se cierra de inmediato y no se puede volver a entrar con ella. En máximo 15 días hábiles borramos tus datos
            personales, tus mascotas, tu ubicación, tus llaves de acceso y tus puntos. Las facturas y los registros contables de
            tus compras se conservan durante el tiempo que exige la ley comercial y tributaria, y después se eliminan.
          </p>
        </section>

        <section>
          <H2>6. Seguridad</H2>
          <p>
            Todo viaja cifrado (HTTPS). La sesión usa cookies seguras que otro sitio no puede leer. Puedes entrar con huella o
            Face ID. Solo el personal que lo necesita accede a los datos. Si ocurre un incidente de seguridad que afecte tus datos,
            lo informaremos a la SIC y a los afectados como exige la ley.
          </p>
        </section>

        <section>
          <H2>7. Cookies</H2>
          <p>
            Usamos cookies propias para mantener tu sesión y tu carrito, y cookies de Google Analytics y Meta para medición.
            Puedes borrarlas o bloquearlas desde tu navegador; la sesión y el carrito dejarían de recordarse.
          </p>
        </section>

        <section>
          <H2>8. Tiempo de conservación</H2>
          <p>
            Guardamos tus datos mientras tengas cuenta o una relación comercial con nosotros, y después solo lo que la ley
            obliga a conservar (facturas y registros contables).
          </p>
        </section>

        <section>
          <H2>9. Cambios a esta política</H2>
          <p>
            Si la cambiamos, publicamos la nueva versión aquí con su fecha y te avisamos en la app o por correo antes de que rija.
          </p>
        </section>
      </div>

      <div className="mt-10 pt-6 border-t border-border flex flex-wrap gap-4 text-sm text-muted-foreground">
        <Link href="/terminos" className="hover:text-brand">Términos y Condiciones</Link>
        <Link href="/devoluciones" className="hover:text-brand">Devoluciones y retracto</Link>
        <Link href="/eliminar-cuenta" className="hover:text-brand">Eliminar mi cuenta</Link>
        <Link href="/contacto" className="hover:text-brand">Contacto</Link>
      </div>
    </div>
  );
}
