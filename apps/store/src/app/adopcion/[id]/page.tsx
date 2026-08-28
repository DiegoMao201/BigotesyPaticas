import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { storeApi } from '@/lib/api';
import { BreadcrumbSchema } from '@/components/seo/JsonLd';
import { MapPin, Phone, ChevronLeft, ClipboardList } from 'lucide-react';

export const revalidate = 300;

function waLink(phone: string, title: string) {
  const digits = phone.replace(/\D/g, '');
  const withCountry = digits.startsWith('57') ? digits : `57${digits}`;
  const text = encodeURIComponent(`Hola! Vi "${title}" en bigotesypaticas.com/adopcion.`);
  return `https://wa.me/${withCountry}?text=${text}`;
}

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const listing = await storeApi.adoptionListingById(params.id);
  if (!listing) return { title: 'Publicación no encontrada — Bigotes y Paticas' };
  const title = `${listing.title} — ${listing.post_type === 'offer' ? 'En adopción' : 'Busca adoptar'} — Bigotes y Paticas`;
  const description = listing.description ?? title;
  return {
    title,
    description,
    alternates: { canonical: `https://bigotesypaticas.com/adopcion/${listing.id}` },
    openGraph: { title, description, url: `https://bigotesypaticas.com/adopcion/${listing.id}`, images: listing.photos[0] ? [listing.photos[0]] : undefined },
  };
}

export default async function AdoptionListingDetailPage({ params }: { params: { id: string } }) {
  const listing = await storeApi.adoptionListingById(params.id);
  if (!listing) notFound();

  const mapsLink = listing.lat != null && listing.lng != null ? `https://www.google.com/maps?q=${listing.lat},${listing.lng}` : null;

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Adopción', url: 'https://bigotesypaticas.com/adopcion' },
          { name: listing.title, url: `https://bigotesypaticas.com/adopcion/${listing.id}` },
        ]}
      />

      <div className="container-wide py-10 max-w-3xl">
        <Link href="/adopcion" className="inline-flex items-center gap-1 text-sm text-muted-foreground mb-6 hover:text-foreground">
          <ChevronLeft className="h-4 w-4" /> Volver al foro de adopción
        </Link>

        {listing.photos.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-6">
            {listing.photos.map((url, i) => (
              <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="aspect-square rounded-2xl overflow-hidden block">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={url} alt={listing.title} className="h-full w-full object-cover" />
              </a>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2 mb-2">
          <h1 className="text-3xl font-display font-extrabold">{listing.title}</h1>
          <span className="text-[10px] font-bold uppercase tracking-wide text-emerald-800 bg-[#E6F5F1] px-2 py-0.5 rounded-full">
            {listing.post_type === 'offer' ? '🏠 En adopción' : '🔍 Busca adoptar'}
          </span>
        </div>
        {(listing.species || listing.breed) && (
          <p className="text-muted-foreground capitalize mb-4">
            {listing.species}{listing.breed ? ` · ${listing.breed}` : ''}
          </p>
        )}
        {listing.description && <p className="text-gray-700 leading-relaxed mb-6">{listing.description}</p>}

        {listing.delivery_notes && (
          <div className="flex gap-3 rounded-2xl border border-border p-4 mb-6">
            <ClipboardList className="h-5 w-5 text-[#187f77] shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold mb-1">Cómo se entrega en adopción</p>
              <p className="text-sm text-gray-600 leading-relaxed">{listing.delivery_notes}</p>
            </div>
          </div>
        )}

        {mapsLink && listing.address && (
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
              <p className="text-sm font-semibold">{listing.address}</p>
              <p className="text-xs text-muted-foreground">Toca para ver la ubicación en el mapa</p>
            </div>
          </a>
        )}

        <a
          href={waLink(listing.contact_phone, listing.title)}
          target="_blank"
          rel="noopener noreferrer"
          className="w-full flex items-center justify-center gap-2 py-4 rounded-xl bg-[#187f77] text-white font-bold text-sm hover:bg-[#0d4a45] transition-colors"
        >
          <Phone className="h-4 w-4" /> Escribir por WhatsApp
        </a>
      </div>
    </>
  );
}
