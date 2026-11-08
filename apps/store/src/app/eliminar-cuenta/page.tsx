import type { Metadata } from 'next';
import { FormEliminar } from './FormEliminar';

// Página pública de eliminación de cuenta (8-nov-2026). Google Play la exige como URL
// en la "Seguridad de los datos" de la ficha: el cliente tiene que poder pedir el borrado
// aunque ya haya desinstalado la app. No se indexa.
export const metadata: Metadata = {
  title: 'Eliminar mi cuenta',
  description: 'Pide la eliminación de tu cuenta de Bigotes y Paticas y de tus datos personales.',
  robots: { index: false, follow: true },
  alternates: { canonical: 'https://bigotesypaticas.com/eliminar-cuenta' },
};

export default function EliminarCuentaPage() {
  return (
    <main className="container-tight max-w-xl py-14">
      <h1 className="font-display text-3xl font-extrabold text-[#0d4a45]">Eliminar mi cuenta</h1>
      <p className="mt-3 text-muted-foreground">
        Si tienes cuenta en la app o en el portal de clientes de Bigotes y Paticas
        (mi.bigotesypaticas.com), puedes pedir aquí que la eliminemos junto con tus datos.
        También puedes hacerlo dentro de la app, en <strong>Perfil → Eliminar mi cuenta</strong>.
      </p>
      <div className="mt-6 rounded-2xl border border-border bg-card p-5 text-sm leading-relaxed">
        <p className="font-semibold">Qué pasa cuando lo pides</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>Tu cuenta se cierra de inmediato en todos tus dispositivos.</li>
          <li>En máximo 15 días hábiles borramos tus datos personales (nombre, teléfono, correo, dirección), tus mascotas y su historial, tu ubicación y tus puntos.</li>
          <li>Conservamos las facturas de tus compras porque la ley tributaria nos obliga a guardarlas.</li>
        </ul>
        <p className="mt-3">
          Es tu derecho de supresión según la Ley 1581 de 2012. Si tienes dudas, escríbenos a{' '}
          <a className="font-semibold text-teal-700 underline" href="mailto:bigotesypaticasdosquebradas@gmail.com">bigotesypaticasdosquebradas@gmail.com</a>{' '}
          o al WhatsApp 320 687 6633.
        </p>
      </div>
      <FormEliminar />
    </main>
  );
}
