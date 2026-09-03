import type { Metadata } from 'next';
import Link from 'next/link';
import { PetPhoto } from '@/components/ui/PetPhoto';
import { notFound } from 'next/navigation';
import { storeApi } from '@/lib/api';
import { BreadcrumbSchema, SuccessStorySchema } from '@/components/seo/JsonLd';
import { CommentsSection } from '@/components/community/CommentsSection';
import { MapPin, Phone, Gift, ChevronLeft, PartyPopper } from 'lucide-react';

export const revalidate = 300;

function waLink(phone: string, petName: string) {
  // Defensa ante datos viejos/mal ingresados (ej. dos números en un solo
  // campo) que generarían un número inválido de más de 12 dígitos y un
  // enlace de WhatsApp roto (404) -- se recorta a un celular colombiano
  // válido en vez de concatenar dígitos de más.
  const digits = phone.replace(/\D/g, '').slice(0, 12);
  const withCountry = digits.startsWith('57') ? digits : `57${digits}`;
  const text = encodeURIComponent(`Hola! Vi el reporte de ${petName} en bigotesypaticas.com y quiero ayudar.`);
  return `https://wa.me/${withCountry}?text=${text}`;
}

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const pet = await storeApi.lostPetById(params.id);
  if (!pet) return { title: 'Reporte no encontrado — Bigotes y Paticas' };
  const url = `https://bigotesypaticas.com/mascotas-perdidas/${pet.id}`;
  if (pet.resolved) {
    const title = `¡${pet.pet_name} ya está en casa! — Mascota encontrada en Pereira/Dosquebradas`;
    const description = pet.resolution_note ?? `${pet.pet_name} volvió a su hogar gracias a la comunidad de Bigotes y Paticas.`;
    return {
      title,
      description,
      alternates: { canonical: url },
      openGraph: { title, description, url, images: pet.photos[0] ? [pet.photos[0]] : undefined },
    };
  }
  const title = `${pet.pet_name} — Mascota perdida en Pereira/Dosquebradas — Bigotes y Paticas`;
  const description = `${pet.pet_name} es ${pet.species}${pet.breed ? `, raza ${pet.breed}` : ''}, color ${pet.color}. Se perdió en Pereira/Dosquebradas. Ayúdanos a encontrarlo.`;
  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: { title, description, url, images: pet.photos[0] ? [pet.photos[0]] : undefined },
  };
}

export default async function LostPetDetailPage({ params }: { params: { id: string } }) {
  const pet = await storeApi.lostPetById(params.id);
  if (!pet) notFound();

  const url = `https://bigotesypaticas.com/mascotas-perdidas/${pet.id}`;
  const mapsLink = `https://www.google.com/maps?q=${pet.last_seen_lat},${pet.last_seen_lng}`;
  const resolved = pet.resolved;

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Mascotas Perdidas', url: 'https://bigotesypaticas.com/mascotas-perdidas' },
          { name: pet.pet_name, url },
        ]}
      />
      {resolved && pet.resolved_at && (
        <SuccessStorySchema
          url={url}
          headline={pet.success_headline ?? `¡${pet.pet_name} ya está en casa!`}
          description={pet.resolution_note ?? ''}
          image={pet.photos[0]}
          datePublished={pet.resolved_at}
          expires={pet.public_until}
        />
      )}

      <div className="container-wide py-10 max-w-3xl">
        <Link href="/mascotas-perdidas" className="inline-flex items-center gap-1 text-sm text-muted-foreground mb-6 hover:text-foreground">
          <ChevronLeft className="h-4 w-4" /> Volver a mascotas perdidas
        </Link>

        {resolved && (
          <div className="rounded-3xl bg-gradient-to-br from-emerald-600 to-emerald-500 text-white p-6 md:p-8 mb-6 shadow-lg">
            <div className="flex items-start gap-4">
              <div className="h-12 w-12 rounded-2xl bg-white/20 flex items-center justify-center shrink-0">
                <PartyPopper className="h-6 w-6" />
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-display font-extrabold leading-tight mb-2">
                  {pet.success_headline ?? `¡${pet.pet_name} ya está en casa! 🎉`}
                </h1>
                <p className="text-white/95 leading-relaxed">{pet.resolution_note}</p>
                {pet.resolved_at && (
                  <p className="text-white/70 text-xs mt-3">
                    {new Date(pet.resolved_at).toLocaleDateString('es-CO', { day: 'numeric', month: 'long', year: 'numeric' })}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        <div className={`rounded-3xl overflow-hidden border bg-card ${resolved ? 'border-emerald-200' : 'border-border'}`}>
          {pet.photos[0] ? (
            <div className="relative w-full h-80 sm:h-96 overflow-hidden bg-[#F8F9FA]">
              <PetPhoto src={pet.photos[0]} alt={pet.pet_name} priority sizes="(max-width: 768px) 100vw, 768px" />
            </div>
          ) : (
            <div className="w-full h-80 bg-gradient-to-br from-[#e8433a] to-[#c62f28] flex items-center justify-center text-8xl">🐾</div>
          )}

          <div className="p-8">
            <div className="flex items-center gap-2 mb-2">
              {resolved ? (
                <h2 className="text-3xl font-display font-extrabold">{pet.pet_name}</h2>
              ) : (
                <h1 className="text-3xl font-display font-extrabold">{pet.pet_name}</h1>
              )}
              {resolved ? (
                <span className="text-[10px] font-bold uppercase tracking-wide text-white bg-emerald-500 px-2 py-0.5 rounded-full">
                  🎉 En casa
                </span>
              ) : (
                <span className="text-[10px] font-bold uppercase tracking-wide text-[#c62f28] bg-[#FDEEE9] px-2 py-0.5 rounded-full">
                  Perdido
                </span>
              )}
            </div>
            <p className="text-muted-foreground capitalize mb-6">
              {pet.species}{pet.breed ? ` · ${pet.breed}` : ''} · {pet.color}
            </p>

            {!resolved && pet.reward != null && pet.reward > 0 && (
              <div className="inline-flex items-center gap-2 rounded-xl bg-emerald-50 text-emerald-700 px-4 py-2 text-sm font-semibold mb-6">
                <Gift className="h-4 w-4" /> Recompensa por su regreso: ${pet.reward.toLocaleString('es-CO')}
              </div>
            )}

            {!resolved && (
              <>
                <a
                  href={mapsLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 rounded-2xl border border-border p-4 mb-6 hover:bg-muted/40 transition-colors"
                >
                  <div className="h-10 w-10 rounded-xl bg-[#FDEEE9] flex items-center justify-center shrink-0">
                    <MapPin className="h-5 w-5 text-[#c62f28]" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold">Última vez visto aquí</p>
                    <p className="text-xs text-muted-foreground">Toca para ver la ubicación en el mapa</p>
                  </div>
                </a>

                <a
                  href={waLink(pet.contact_phone, pet.pet_name)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full flex items-center justify-center gap-2 py-4 rounded-xl bg-[#e8433a] text-white font-bold text-sm hover:bg-[#c62f28] transition-colors"
                >
                  <Phone className="h-4 w-4" /> Escribir por WhatsApp
                </a>
              </>
            )}

            {resolved && (
              <p className="text-sm text-muted-foreground">
                Este caso ya se resolvió. Si tu mascota se perdió,{' '}
                <Link href="https://mi.bigotesypaticas.com/sos/new" className="font-semibold text-[#c62f28]">repórtala aquí</Link> y
                la comunidad te ayuda a encontrarla.
              </p>
            )}
          </div>
        </div>

        <CommentsSection
          entityType="lost"
          entityId={pet.id}
          accent={resolved ? '#059669' : '#c62f28'}
          placeholder={resolved ? `¡Qué alegría que ${pet.pet_name} esté en casa! Deja tu mensaje…` : `¿Viste a ${pet.pet_name}? ¿Quieres mandar ánimo a su familia? Escribe aquí…`}
        />

        <div className="mt-8 rounded-2xl bg-[#f5f0e8] p-6 text-center">
          <p className="text-sm text-gray-600">
            {resolved ? (
              <>Mira más <Link href="/finales-felices" className="font-semibold text-[#187f77]">finales felices de la comunidad</Link>.</>
            ) : (
              <>¿Encontraste una mascota y no sabes de quién es?{' '}<Link href="/mascotas-encontradas" className="font-semibold text-[#187f77]">Publícala aquí</Link>.</>
            )}
          </p>
        </div>
      </div>
    </>
  );
}
