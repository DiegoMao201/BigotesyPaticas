import { Heart, MapPin, Phone, Mail } from 'lucide-react';
import Link from 'next/link';

export const metadata = {
  title: 'Nuestra historia',
  description: 'Conoce a Bigotes y Paticas, la tienda de mascotas premium en Dosquebradas y Pereira.',
};

export default function NosotrosPage() {
  return (
    <div className="container-tight py-16">
      <div className="max-w-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-teal-50 border border-teal-100 text-teal-700 text-xs font-semibold mb-6">
          <Heart className="h-3.5 w-3.5 fill-teal-500" /> Nuestra historia
        </div>
        <h1 className="text-5xl font-display font-bold leading-tight mb-8">
          Amor por las mascotas, desde Dosquebradas
        </h1>
        <div className="space-y-5 text-muted-foreground leading-relaxed text-lg">
          <p>
            Bigotes y Paticas nació del amor profundo por las mascotas. Sabemos que cada lengüetazo,
            cada ronroneo y cada cola que se mueve es una declaración de cariño.
          </p>
          <p>
            Por eso seleccionamos personalmente cada producto que ofrecemos: comida premium, accesorios
            de la mejor calidad y artículos de cuidado avalados por veterinarios.
          </p>
          <p>
            Estamos ubicados en <strong className="text-foreground">Dosquebradas, Risaralda</strong>,
            y entregamos en toda la zona urbana de Pereira y Dosquebradas. Nuestro compromiso es
            simple: si no se lo daríamos a nuestra propia mascota, no lo vendemos.
          </p>
        </div>

        <div className="mt-12 grid sm:grid-cols-3 gap-6">
          <div className="rounded-2xl border border-border bg-card p-5 flex flex-col gap-2">
            <div className="text-3xl">🐶</div>
            <div className="font-display font-bold text-lg">+500 productos</div>
            <p className="text-sm text-muted-foreground">Catálogo curado por expertos</p>
          </div>
          <div className="rounded-2xl border border-border bg-card p-5 flex flex-col gap-2">
            <div className="text-3xl">⭐</div>
            <div className="font-display font-bold text-lg">4.9 / 5</div>
            <p className="text-sm text-muted-foreground">Satisfacción de nuestros clientes</p>
          </div>
          <div className="rounded-2xl border border-border bg-card p-5 flex flex-col gap-2">
            <div className="text-3xl">🚚</div>
            <div className="font-display font-bold text-lg">24 - 72 horas</div>
            <p className="text-sm text-muted-foreground">Entrega rápida en tu zona</p>
          </div>
        </div>

        <div className="mt-12 rounded-2xl bg-teal-50 border border-teal-100 p-6 space-y-3">
          <h2 className="font-display font-bold text-lg text-teal-900">Encuéntranos</h2>
          <ul className="space-y-2 text-sm text-teal-800">
            <li className="flex items-center gap-2.5">
              <MapPin className="h-4 w-4 text-teal-600 shrink-0" />
              Dosquebradas, Risaralda — Pereira y Dosquebradas zona urbana
            </li>
            <li className="flex items-center gap-2.5">
              <Phone className="h-4 w-4 text-teal-600 shrink-0" />
              <a href="tel:+573206876633" className="hover:underline">+57 320 687 6633</a>
            </li>
            <li className="flex items-center gap-2.5">
              <Mail className="h-4 w-4 text-teal-600 shrink-0" />
              <a href="mailto:bigotesypaticasdosquebradas@gmail.com" className="hover:underline break-all">
                bigotesypaticasdosquebradas@gmail.com
              </a>
            </li>
          </ul>
        </div>

        <div className="mt-8 flex gap-3">
          <Link href="/categorias/perros"
            className="px-5 py-3 rounded-2xl gradient-brand text-white font-semibold text-sm shadow-md hover:opacity-90 transition-opacity">
            Ver productos
          </Link>
          <Link href="/contacto"
            className="px-5 py-3 rounded-2xl border border-border font-semibold text-sm hover:bg-secondary transition-colors">
            Contáctanos
          </Link>
        </div>
      </div>
    </div>
  );
}
