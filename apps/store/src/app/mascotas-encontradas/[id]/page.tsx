import type { Metadata } from 'next';
import Link from 'next/link';
import Image from 'next/image';
import { notFound } from 'next/navigation';
import { storeApi } from '@/lib/api';
import { BreadcrumbSchema } from '@/components/seo/JsonLd';
import { MapPin, Phone, ChevronLeft, CheckCircle2 } from 'lucide-react';

export const revalidate = 300;

function waLink(phone: string, title: string) {
  // Defensa ante datos viejos/mal ingresados (ej. dos números en un solo
  // campo) que generarían un número inválido de más de 12 dígitos y un
  // enlace de WhatsApp roto (404) -- se recorta a un celular colombiano
  // válido en vez de concatenar dígitos de más.
  const digits = phone.replace(/\D/g, '').slice(0, 12);
  const withCountry = digits.startsWith('57') ? digits : `57${digits}`;
  const text = encodeURIComponent(`Hola! Vi "${title}" en bigotesypaticas.com y creo que puede ser mi mascota.`);
  return `https://wa.me/${withCountry}?text=${text}`;
}

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const ev = await storeApi.foundEventById(params.id);
  if (!ev) return { title: 'Evento no encontrado — Bigotes y Paticas' };
  const title = `${ev.title} — Animales encontrados en Pereira/Dosquebradas`;
  const description = ev.description ?? `${ev.animal_count} animalito(s) encontrados en ${ev.address ?? 'Pereira/Dosquebradas'}, esperando a su familia.`;
  return {
    title,
    description,
    alternates: { canonical: `https://bigotesypaticas.com/mascotas-encontradas/${ev.id}` },
    openGraph: { title, description, url: `https://bigotesypaticas.com/mascotas-encontradas/${ev.id}`, images: ev.cover_thumb_url ? [ev.cover_thumb_url] : undefined },
  };
}

export default async function FoundEventDetailPage({ params }: { params: { id: string } }) {
  const ev = await storeApi.foundEventById(params.id);
  if (!ev) notFound();

  const mapsLink = `https://www.google.com/maps?q=${ev.lat},${ev.lng}`;

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Animales Encontrados', url: 'https://bigotesypaticas.com/mascotas-encontradas' },
          { name: ev.title, url: `https://bigotesypaticas.com/mascotas-encontradas/${ev.id}` },
        ]}
      />

      <div className="container-wide py-10 max-w-3xl">
        <Link href="/mascotas-encontradas" className="inline-flex items-center gap-1 text-sm text-muted-foreground mb-6 hover:text-foreground">
          <ChevronLeft className="h-4 w-4" /> Volver a animales encontrados
        </Link>

        <h1 className="text-3xl font-display font-extrabold mb-2">{ev.title}</h1>
        {ev.description && <p className="text-muted-foreground mb-6 leading-relaxed">{ev.description}</p>}

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-8">
          {ev.animals.map((a) => (
            <a key={a.id} href={a.photo_url} target="_blank" rel="noopener noreferrer" className="relative aspect-square rounded-2xl overflow-hidden block">
              <Image
                src={a.thumb_url ?? a.photo_url}
                alt={a.description ?? ev.title}
                fill
                sizes="(max-width: 640px) 50vw, 33vw"
                className="object-cover"
              />
              {a.status === 'reunited' && (
                <span className="absolute inset-0 bg-black/50 flex items-center justify-center">
                  <span className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                    <CheckCircle2 className="h-3 w-3" /> Reunido
                  </span>
                </span>
              )}
            </a>
          ))}
        </div>

        {ev.address && (
          <a
            href={mapsLink}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 rounded-2xl border border-border p-4 mb-6 hover:bg-muted/40 transition-colors"
          >
            <div className="h-10 w-10 rounded-xl bg-[#E6F5F1] flex items-center justify-center shrink-0">
              <MapPin className="h-5 w-5 text-[#187f77]" />
            </div>
            <div>
              <p className="text-sm font-semibold">{ev.address}</p>
              <p className="text-xs text-muted-foreground">Toca para ver la ubicación en el mapa</p>
            </div>
          </a>
        )}

        {ev.contact_phone && (
          <a
            href={waLink(ev.contact_phone, ev.title)}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full flex items-center justify-center gap-2 py-4 rounded-xl bg-[#187f77] text-white font-bold text-sm hover:bg-[#0d4a45] transition-colors"
          >
            <Phone className="h-4 w-4" /> Escribir por WhatsApp
          </a>
        )}

        <div className="mt-8 rounded-2xl bg-[#f5f0e8] p-6 text-center">
          <p className="text-sm text-gray-600">
            ¿Se te perdió tu mascota?{' '}
            <Link href="/mascotas-perdidas" className="font-semibold text-[#c62f28]">
              Repórtala aquí
            </Link>
            .
          </p>
        </div>
      </div>
    </>
  );
}
