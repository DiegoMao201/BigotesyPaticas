import type { Metadata } from 'next';
import Link from 'next/link';
import { PetPhoto } from '@/components/ui/PetPhoto';
import { notFound } from 'next/navigation';
import { storeApi } from '@/lib/api';
import { BreadcrumbSchema, SuccessStorySchema } from '@/components/seo/JsonLd';
import { CommentsSection } from '@/components/community/CommentsSection';
import { MapPin, Phone, ChevronLeft, ClipboardList, PartyPopper } from 'lucide-react';

export const revalidate = 300;

function waLink(phone: string, title: string) {
  // Defensa ante datos viejos/mal ingresados (ej. dos números en un solo
  // campo) que generarían un número inválido de más de 12 dígitos y un
  // enlace de WhatsApp roto (404) -- se recorta a un celular colombiano
  // válido en vez de concatenar dígitos de más.
  const digits = phone.replace(/\D/g, '').slice(0, 12);
  const withCountry = digits.startsWith('57') ? digits : `57${digits}`;
  const text = encodeURIComponent(`Hola! Vi "${title}" en bigotesypaticas.com/adopcion.`);
  return `https://wa.me/${withCountry}?text=${text}`;
}

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const listing = await storeApi.adoptionListingById(params.id);
  if (!listing) return { title: 'Publicación no encontrada — Bigotes y Paticas' };
  const url = `https://bigotesypaticas.com/adopcion/${listing.id}`;
  if (listing.resolved) {
    const title = `${listing.success_headline ?? (listing.post_type === 'want' ? '¡Ya adoptó!' : '¡Encontró un hogar!')} ${listing.title} — Adopción en Pereira/Dosquebradas`;
    const description = listing.resolution_note ?? listing.outcome_note ?? `${listing.title}: historia de éxito del foro de adopción de Bigotes y Paticas.`;
    return { title, description, alternates: { canonical: url }, openGraph: { title, description, url, images: listing.photos[0] ? [listing.photos[0]] : undefined } };
  }
  const title = `${listing.title} — ${listing.post_type === 'offer' ? 'En adopción' : 'Busca adoptar'} — Bigotes y Paticas`;
  const description = listing.description ?? title;
  return { title, description, alternates: { canonical: url }, openGraph: { title, description, url, images: listing.photos[0] ? [listing.photos[0]] : undefined } };
}

export default async function AdoptionListingDetailPage({ params }: { params: { id: string } }) {
  const listing = await storeApi.adoptionListingById(params.id);
  if (!listing) notFound();

  const url = `https://bigotesypaticas.com/adopcion/${listing.id}`;
  const mapsLink = listing.lat != null && listing.lng != null ? `https://www.google.com/maps?q=${listing.lat},${listing.lng}` : null;
  const resolved = listing.resolved;

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Adopción', url: 'https://bigotesypaticas.com/adopcion' },
          { name: listing.title, url },
        ]}
      />
      {resolved && listing.resolved_at && (
        <SuccessStorySchema
          url={url}
          headline={`${listing.success_headline ?? '¡Final feliz!'} ${listing.title}`}
          description={listing.resolution_note ?? listing.outcome_note ?? ''}
          image={listing.photos[0]}
          datePublished={listing.resolved_at}
          expires={listing.public_until}
        />
      )}

      <div className="container-wide py-10 max-w-3xl">
        <Link href="/adopcion" className="inline-flex items-center gap-1 text-sm text-muted-foreground mb-6 hover:text-foreground">
          <ChevronLeft className="h-4 w-4" /> Volver al foro de adopción
        </Link>

        {resolved && (
          <div className="rounded-3xl bg-gradient-to-br from-emerald-600 to-emerald-500 text-white p-6 md:p-8 mb-6 shadow-lg">
            <div className="flex items-start gap-4">
              <div className="h-12 w-12 rounded-2xl bg-white/20 flex items-center justify-center shrink-0">
                <PartyPopper className="h-6 w-6" />
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-display font-extrabold leading-tight mb-2">
                  {listing.success_headline ?? '¡Final feliz! 🎉'}
                </h1>
                <p className="text-white/95 leading-relaxed">{listing.resolution_note ?? listing.outcome_note}</p>
                {listing.resolved_at && (
                  <p className="text-white/70 text-xs mt-3">
                    {new Date(listing.resolved_at).toLocaleDateString('es-CO', { day: 'numeric', month: 'long', year: 'numeric' })}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {listing.photos.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-6">
            {listing.photos.map((url2, i) => (
              <a key={i} href={url2} target="_blank" rel="noopener noreferrer" className="relative aspect-square rounded-2xl overflow-hidden block bg-[#F8F9FA]">
                <PetPhoto src={url2} alt={listing.title} sizes="(max-width: 640px) 50vw, 33vw" />
              </a>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2 mb-2 flex-wrap">
          {resolved ? (
            <h2 className="text-3xl font-display font-extrabold">{listing.title}</h2>
          ) : (
            <h1 className="text-3xl font-display font-extrabold">{listing.title}</h1>
          )}
          <span className="text-[10px] font-bold uppercase tracking-wide text-emerald-800 bg-[#E6F5F1] px-2 py-0.5 rounded-full">
            {listing.post_type === 'offer' ? '🏠 En adopción' : '🔍 Busca adoptar'}
          </span>
          {resolved && (
            <span className="text-[10px] font-bold uppercase tracking-wide text-white bg-emerald-500 px-2 py-0.5 rounded-full">
              🎉 {listing.post_type === 'want' ? 'Ya adoptó' : 'Adoptado'}
            </span>
          )}
        </div>
        {(listing.species || listing.breed) && (
          <p className="text-muted-foreground capitalize mb-4">
            {listing.species}{listing.breed ? ` · ${listing.breed}` : ''}
          </p>
        )}
        {listing.description && <p className="text-gray-700 leading-relaxed mb-6">{listing.description}</p>}

        {!resolved && listing.delivery_notes && (
          <div className="flex gap-3 rounded-2xl border border-border p-4 mb-6">
            <ClipboardList className="h-5 w-5 text-[#187f77] shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold mb-1">Cómo se entrega en adopción</p>
              <p className="text-sm text-gray-600 leading-relaxed">{listing.delivery_notes}</p>
            </div>
          </div>
        )}

        {!resolved && mapsLink && listing.address && (
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

        {!resolved && (
          <a
            href={waLink(listing.contact_phone, listing.title)}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full flex items-center justify-center gap-2 py-4 rounded-xl bg-[#187f77] text-white font-bold text-sm hover:bg-[#0d4a45] transition-colors"
          >
            <Phone className="h-4 w-4" /> Escribir por WhatsApp
          </a>
        )}

        {resolved && (
          <p className="text-sm text-muted-foreground">
            Esta publicación ya tuvo su final feliz. ¿Quieres adoptar o dar en adopción?{' '}
            <Link href="/adopcion#foro" className="font-semibold text-[#187f77]">Publica en el foro</Link>.
          </p>
        )}

        <CommentsSection
          entityType="adoption"
          entityId={listing.id}
          accent={resolved ? '#059669' : '#187f77'}
          placeholder={resolved ? '¡Qué buena noticia! Deja tu mensaje…' : 'Pregunta, comenta o manda ánimo…'}
        />

        <p className="text-center text-xs text-muted-foreground mt-8 leading-relaxed">
          Bigotes y Paticas conecta a quienes tienen un animal en adopción con quienes desean adoptar — no
          gestionamos ni somos responsables del proceso de adopción en sí. Requisitos y seguimiento son un acuerdo
          directo entre las partes.
        </p>
      </div>
    </>
  );
}
