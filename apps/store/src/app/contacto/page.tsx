import type { Metadata } from 'next';
import { Phone, Mail, MapPin, Clock, ExternalLink } from 'lucide-react';
import { ContactForm } from './ContactForm';
import { DeliveryZoneChecker } from '@/components/maps/DeliveryZoneChecker';
import { StoreMapEmbed } from '@/components/maps/StoreMapEmbed';
import { BreadcrumbSchema } from '@/components/seo/JsonLd';
import { BUSINESS_INFO } from '@/lib/business-info';

export const metadata: Metadata = {
  title: 'Contacto — Bigotes y Paticas Pereira y Dosquebradas',
  description:
    'Contáctanos por WhatsApp, teléfono o correo. Pet shop con domicilio en Pereira y Dosquebradas, Risaralda. Horario: Lunes a Sábado 10am-7pm. Mall Zamara Plaza, Dosquebradas.',
  alternates: { canonical: 'https://bigotesypaticas.com/contacto' },
  openGraph: {
    title: 'Contacto — Bigotes y Paticas',
    description: 'Escríbenos por WhatsApp o rellena el formulario. Domicilios en Pereira y Dosquebradas.',
    url: 'https://bigotesypaticas.com/contacto',
  },
};

const GOOGLE_MAPS_URL = 'https://www.google.com/maps/search/?api=1&query=Bigotes+y+Paticas+Mall+Zamara+Plaza+Dosquebradas';

export default function ContactoPage() {
  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Contacto', url: 'https://bigotesypaticas.com/contacto' },
        ]}
      />

      <div className="container-tight py-16 space-y-12">
        {/* Header */}
        <div>
          <p className="text-brand-600 font-semibold text-sm mb-1">Estamos aquí para ti</p>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold mb-3">Contáctanos</h1>
          <p className="text-muted-foreground text-lg max-w-xl">
            Pet shop con domicilio en Pereira y Dosquebradas. Escríbenos y te respondemos pronto.
          </p>
        </div>

        {/* MAPA GRANDE — Google Business Profile */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MapPin className="h-5 w-5 text-brand-600" />
              <div>
                <p className="font-display font-bold">{BUSINESS_INFO.address.streetAddress}</p>
                <p className="text-sm text-muted-foreground">
                  {BUSINESS_INFO.address.addressLocality}, {BUSINESS_INFO.address.addressRegion} · Colombia
                </p>
              </div>
            </div>
            <a
              href={GOOGLE_MAPS_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm font-semibold text-brand-600 hover:text-brand-500 transition-colors"
            >
              Abrir en Google Maps <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
          <StoreMapEmbed height={460} zoom={17} />
        </div>

        {/* Dos columnas: info + formulario */}
        <div className="grid md:grid-cols-5 gap-10">
          {/* Columna izquierda */}
          <div className="md:col-span-2 space-y-5">
            {/* Datos de contacto */}
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
                <li className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-xl bg-teal-700 flex items-center justify-center text-white shrink-0 mt-0.5">
                    <MapPin className="h-4 w-4" />
                  </div>
                  <address className="not-italic">
                    Mall Zamara Plaza, Cl. 15 #3A-07 Local 2<br />
                    <span className="opacity-70">Dosquebradas, Risaralda</span>
                  </address>
                </li>
                <li className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-teal-700 flex items-center justify-center text-white shrink-0">
                    <Clock className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="font-medium">Lun–Sáb · 10:00 am – 7:00 pm</p>
                    <p className="text-xs opacity-70 mt-0.5">Domicilios 24-72h hábiles</p>
                  </div>
                </li>
              </ul>
            </div>

            {/* Verificador zona */}
            <DeliveryZoneChecker />

            {/* WhatsApp directo */}
            <a
              href="https://wa.me/573206876633?text=Hola!%20Tengo%20una%20pregunta%20sobre%20Bigotes%20y%20Paticas"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 px-5 py-3.5 rounded-2xl bg-green-500 text-white font-semibold text-sm hover:bg-green-600 transition-colors shadow-md w-full justify-center"
            >
              <span className="text-lg">💬</span> Chatear por WhatsApp
            </a>
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
