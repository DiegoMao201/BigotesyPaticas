import type { Metadata } from 'next';
import { Phone, Mail, MapPin } from 'lucide-react';
import { ContactForm } from './ContactForm';
import { LocalBusinessSchema, BreadcrumbSchema } from '@/components/seo/JsonLd';

export const metadata: Metadata = {
  title: 'Contacto — Bigotes y Paticas Pereira y Dosquebradas',
  description:
    'Contáctanos por WhatsApp, teléfono o correo. Tienda de mascotas con domicilio en Pereira y Dosquebradas, Risaralda. Horario: Lunes a Sábado 9am-7pm.',
  alternates: { canonical: 'https://bigotesypaticas.com/contacto' },
  openGraph: {
    title: 'Contacto — Bigotes y Paticas',
    description: 'Escríbenos por WhatsApp o rellena el formulario. Domicilios en Pereira y Dosquebradas.',
    url: 'https://bigotesypaticas.com/contacto',
  },
};

export default function ContactoPage() {
  return (
    <>
      <LocalBusinessSchema />
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Contacto', url: 'https://bigotesypaticas.com/contacto' },
        ]}
      />

      <div className="container-tight py-16">
        <div className="mb-10">
          <p className="text-brand-600 font-semibold text-sm mb-1">Estamos aquí para ti</p>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold mb-3">Contáctanos</h1>
          <p className="text-muted-foreground text-lg max-w-md">
            ¿Preguntas sobre un producto, un pedido o domicilios en Pereira y Dosquebradas?
            Escríbenos y te respondemos pronto.
          </p>
        </div>

        <div className="grid md:grid-cols-5 gap-10">
          {/* Info lateral */}
          <div className="md:col-span-2 space-y-6">
            <div className="rounded-2xl bg-teal-50 border border-teal-100 p-6 space-y-4">
              <h2 className="font-display font-bold text-lg text-teal-900">Información de contacto</h2>
              <ul className="space-y-3 text-sm text-teal-800">
                <li className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-teal-700 flex items-center justify-center text-white shrink-0">
                    <Phone className="h-4 w-4" />
                  </div>
                  <a href="tel:+573206876633" className="hover:underline font-medium">
                    +57 320 687 6633
                  </a>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-xl bg-teal-700 flex items-center justify-center text-white shrink-0 mt-0.5">
                    <Mail className="h-4 w-4" />
                  </div>
                  <a href="mailto:bigotesypaticasdosquebradas@gmail.com" className="hover:underline break-all">
                    bigotesypaticasdosquebradas@gmail.com
                  </a>
                </li>
                <li className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-teal-700 flex items-center justify-center text-white shrink-0">
                    <MapPin className="h-4 w-4" />
                  </div>
                  <address className="not-italic">
                    Dosquebradas, Risaralda<br />
                    <span className="text-xs opacity-70">Colombia</span>
                  </address>
                </li>
              </ul>

              <div className="pt-2 border-t border-teal-200">
                <p className="text-xs font-semibold text-teal-700 mb-1">Horario de atención</p>
                <p className="text-xs text-teal-600">Lunes a Sábado · 9:00 am – 7:00 pm</p>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card p-6 space-y-3">
              <h3 className="font-display font-semibold">Zona de entrega</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Entregamos en toda la <strong>zona urbana de Pereira y Dosquebradas</strong>.
                Envío gratis en compras desde $30.000.
              </p>
              <div className="text-sm text-muted-foreground">
                🕐 Tiempo de entrega: <strong>24-72 horas</strong>
              </div>
            </div>

            <a
              href="https://wa.me/573206876633?text=Hola!%20Tengo%20una%20pregunta%20sobre%20Bigotes%20y%20Paticas"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 px-5 py-3 rounded-2xl bg-green-500 text-white font-semibold text-sm hover:bg-green-600 transition-colors shadow-md w-full justify-center"
            >
              <span className="text-lg">💬</span> Chatear por WhatsApp
            </a>

            {/* Mapa */}
            <div className="rounded-2xl overflow-hidden border border-border">
              <iframe
                src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d254508.31843989826!2d-75.7814!3d4.8390!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8e38861a56f1d8f3%3A0x5e6b2b62c7f3e4e8!2sDosquebradas%2C%20Risaralda!5e0!3m2!1ses!2sco!4v1720000000000"
                width="100%"
                height="220"
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                title="Bigotes y Paticas en Dosquebradas, Risaralda"
                className="border-0"
              />
            </div>
          </div>

          {/* Formulario */}
          <div className="md:col-span-3">
            <div className="rounded-3xl border border-border bg-card p-8">
              <h2 className="font-display font-bold text-xl mb-6">Envíanos un mensaje</h2>
              <ContactForm />
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
