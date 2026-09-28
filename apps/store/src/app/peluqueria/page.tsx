import type { Metadata } from 'next';
import { MapPin, Clock, Phone, Star, Scissors, Bath, Sparkles, PawPrint } from 'lucide-react';
import { BreadcrumbSchema, FAQPageSchema } from '@/components/seo/JsonLd';
import { BUSINESS_INFO } from '@/lib/business-info';
import { ReservaPeluqueria } from './ReservaPeluqueria';

/**
 * Peluquería canina y felina (28-sep-2026). Destino del anuncio de Google Ads y página para
 * posicionar "peluquería canina Dosquebradas/Pereira" (0 de 21 puntos en el mapa ese día).
 * Reserva sin cuenta. Solo datos confirmados: servicios, horario, 10% en línea, reseñas.
 * Sin precios hasta que Diego los confirme: se dicen por WhatsApp según tamaño y pelaje.
 */

const BASE = 'https://bigotesypaticas.com';
const URL = `${BASE}/peluqueria`;
const WA_TXT = encodeURIComponent('Hola, quiero información de la peluquería para mi mascota 🐾');

export const metadata: Metadata = {
  title: { absolute: 'Peluquería Canina y Felina en Dosquebradas y Pereira' },
  description:
    'Baño, corte, cepillado y corte de uñas para perros y gatos en Samara Plaza Mall, Dosquebradas. Reserva en línea sin registrarte y recibe 10% de descuento.',
  alternates: { canonical: URL },
  openGraph: {
    title: 'Peluquería canina y felina · Bigotes y Paticas',
    description: 'Reserva en línea la peluquería de tu perro o gato y recibe 10% de descuento.',
    url: URL,
    images: [{ url: `${BASE}/peluqueria/fachada.jpg`, width: 700, height: 393 }],
  },
};

const SERVICIOS = [
  { icono: Bath, titulo: 'Baño', texto: 'Con productos para su tipo de pelo y piel.' },
  { icono: Scissors, titulo: 'Corte', texto: 'Corte y arreglo según la raza o como lo prefieras.' },
  { icono: Sparkles, titulo: 'Cepillado', texto: 'Quitamos el pelo muerto y los nudos.' },
  { icono: PawPrint, titulo: 'Corte de uñas', texto: 'Para que camine cómodo y no se lastime.' },
];

const FAQS = [
  {
    pregunta: '¿Atienden perros y gatos?',
    respuesta: 'Sí. La peluquería es canina y felina: baño, corte, cepillado y corte de uñas para perros y gatos.',
  },
  {
    pregunta: '¿Cuál es el horario de la peluquería?',
    respuesta: 'De lunes a sábado, de 10 a. m. a 7 p. m., en Samara Plaza Mall, Local 2, Dosquebradas.',
  },
  {
    pregunta: '¿Cuánto cuesta el baño?',
    respuesta:
      'Depende del tamaño y del tipo de pelo de tu mascota. Cuando reservas te escribimos por WhatsApp con el precio exacto antes de la cita, y por reservar en línea tienes 10% de descuento.',
  },
  {
    pregunta: '¿Tengo que registrarme para reservar?',
    respuesta: 'No. Eliges el día y la hora, escribes tu nombre y tu celular, y te confirmamos por WhatsApp.',
  },
];

export default function PeluqueriaPage() {
  const tel = BUSINESS_INFO.phone;
  return (
    <>
      <BreadcrumbSchema items={[{ name: 'Inicio', url: BASE }, { name: 'Peluquería canina y felina', url: URL }]} />
      <FAQPageSchema faqs={FAQS} />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Service',
            name: 'Peluquería canina y felina',
            serviceType: 'Pet grooming',
            description: 'Baño, corte, cepillado y corte de uñas para perros y gatos.',
            url: URL,
            areaServed: BUSINESS_INFO.areaServed.map((c) => ({ '@type': 'City', name: c })),
            provider: {
              '@type': 'PetStore',
              name: BUSINESS_INFO.name,
              telephone: tel,
              url: BASE,
              address: { '@type': 'PostalAddress', ...BUSINESS_INFO.address },
            },
          }),
        }}
      />

      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-[#0d4a45] via-[#187f77] to-[#1fa393] text-white">
        <div className="container-wide grid grid-cols-1 gap-8 py-10 md:py-14 lg:grid-cols-2 lg:items-start">
          <div className="min-w-0 pt-2">
            <p className="text-sm font-bold uppercase tracking-[0.2em] text-[#B2FF59]">¡Volvió la peluquería!</p>
            <h1 className="mt-2 text-3xl sm:text-4xl md:text-5xl font-display font-extrabold leading-tight break-words">
              Peluquería canina y felina en Dosquebradas
            </h1>
            <p className="mt-4 text-lg text-white/90">
              Baño, corte, cepillado y corte de uñas para tu perro o tu gato, a pocos minutos de Pereira.
            </p>
            <div className="mt-5 inline-flex items-center gap-3 rounded-2xl bg-white/10 px-4 py-3 backdrop-blur">
              <span className="text-4xl font-black text-[#F5A641] leading-none">10%</span>
              <span className="text-sm leading-snug">de descuento<br />reservando en línea</span>
            </div>
            <ul className="mt-6 space-y-2 text-white/90">
              <li className="flex items-center gap-2"><Clock className="h-5 w-5 text-[#B2FF59]" /> Lunes a sábado · 10 a. m. a 7 p. m.</li>
              <li className="flex items-center gap-2"><MapPin className="h-5 w-5 text-[#B2FF59]" /> Samara Plaza Mall, Local 2 · Dosquebradas</li>
              <li className="flex items-center gap-2">
                <Star className="h-5 w-5 fill-[#F5A641] text-[#F5A641]" />
                <a href={BUSINESS_INFO.mapsUrl} target="_blank" rel="noopener noreferrer" className="underline decoration-white/40">
                  5,0 en Google con más de 30 reseñas
                </a>
              </li>
            </ul>
            <div className="mt-6 flex flex-wrap gap-3">
              <a href={`https://wa.me/${BUSINESS_INFO.whatsapp}?text=${WA_TXT}`} target="_blank" rel="noopener noreferrer"
                className="rounded-2xl bg-[#25D366] px-5 py-3 font-bold text-white shadow-md hover:brightness-95">
                Preguntar por WhatsApp
              </a>
              <a href={`tel:${tel}`} className="flex items-center gap-2 rounded-2xl bg-white/15 px-5 py-3 font-bold hover:bg-white/25">
                <Phone className="h-4 w-4" /> Llamar
              </a>
            </div>
          </div>

          <div id="reservar" className="min-w-0 scroll-mt-24">
            <ReservaPeluqueria />
          </div>
        </div>
      </section>

      {/* Qué incluye */}
      <section className="container-wide py-12">
        <h2 className="text-2xl md:text-3xl font-display font-bold text-[#0d4a45] mb-6">Qué hacemos</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {SERVICIOS.map(({ icono: Icono, titulo, texto }) => (
            <div key={titulo} className="rounded-2xl border border-[#e8e0d0] bg-[#f9f7f3] p-5">
              <Icono className="h-7 w-7 text-[#187f77] mb-3" />
              <h3 className="font-bold text-[#0d4a45]">{titulo}</h3>
              <p className="mt-1 text-sm text-gray-600">{texto}</p>
            </div>
          ))}
        </div>
        <p className="mt-5 text-sm text-gray-600">
          El precio depende del tamaño y del tipo de pelo. Cuando reservas te escribimos por WhatsApp con el valor exacto antes de la cita.
        </p>
      </section>

      {/* Dónde */}
      <section className="bg-[#f9f7f3] py-12">
        <div className="container-wide grid gap-8 md:grid-cols-2 md:items-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/peluqueria/fachada.jpg" alt="Entrada de Bigotes y Paticas en Samara Plaza Mall, Dosquebradas"
            width={700} height={393} loading="lazy" className="w-full rounded-3xl shadow-lg" />
          <div>
            <h2 className="text-2xl md:text-3xl font-display font-bold text-[#0d4a45]">Dónde estamos</h2>
            <p className="mt-3 text-gray-700">
              {BUSINESS_INFO.address.streetAddress}, {BUSINESS_INFO.address.addressLocality}. Atendemos a Dosquebradas y Pereira.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <a href={BUSINESS_INFO.mapsUrl} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-2xl bg-[#187f77] px-5 py-3 font-bold text-white hover:brightness-110">
                <MapPin className="h-4 w-4" /> Cómo llegar
              </a>
              <a href="#reservar" className="rounded-2xl border-2 border-[#187f77] px-5 py-3 font-bold text-[#187f77] hover:bg-teal-50">
                Reservar cita
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Preguntas */}
      <section className="container-wide py-12">
        <h2 className="text-2xl md:text-3xl font-display font-bold text-[#0d4a45] mb-6">Preguntas frecuentes</h2>
        <div className="space-y-3 max-w-3xl">
          {FAQS.map((f) => (
            <details key={f.pregunta} className="rounded-2xl border border-gray-200 p-5 open:shadow-sm">
              <summary className="cursor-pointer font-semibold text-[#0d4a45]">{f.pregunta}</summary>
              <p className="mt-2 text-gray-600">{f.respuesta}</p>
            </details>
          ))}
        </div>
        <p className="mt-8 text-sm text-gray-500">
          ¿Ya eres cliente del portal?{' '}
          <a href="https://mi.bigotesypaticas.com/appointments/new" className="font-semibold text-[#187f77] underline">
            Reserva desde tu cuenta
          </a>{' '}
          y suma puntos Bigotes.
        </p>
      </section>
    </>
  );
}
