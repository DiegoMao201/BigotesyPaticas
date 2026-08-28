import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { storeApi } from '@/lib/api';
import { BreadcrumbSchema } from '@/components/seo/JsonLd';
import { MapPin, Phone, Gift, ChevronLeft } from 'lucide-react';

export const revalidate = 300;

function waLink(phone: string, petName: string) {
  const digits = phone.replace(/\D/g, '');
  const withCountry = digits.startsWith('57') ? digits : `57${digits}`;
  const text = encodeURIComponent(`Hola! Vi el reporte de ${petName} en bigotesypaticas.com y quiero ayudar.`);
  return `https://wa.me/${withCountry}?text=${text}`;
}

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const pet = await storeApi.lostPetById(params.id);
  if (!pet) return { title: 'Reporte no encontrado — Bigotes y Paticas' };
  const title = `${pet.pet_name} — Mascota perdida en Pereira/Dosquebradas — Bigotes y Paticas`;
  const description = `${pet.pet_name} es ${pet.species}${pet.breed ? `, raza ${pet.breed}` : ''}, color ${pet.color}. Se perdió en Pereira/Dosquebradas. Ayúdanos a encontrarlo.`;
  return {
    title,
    description,
    alternates: { canonical: `https://bigotesypaticas.com/mascotas-perdidas/${pet.id}` },
    openGraph: { title, description, url: `https://bigotesypaticas.com/mascotas-perdidas/${pet.id}`, images: pet.photos[0] ? [pet.photos[0]] : undefined },
  };
}

export default async function LostPetDetailPage({ params }: { params: { id: string } }) {
  const pet = await storeApi.lostPetById(params.id);
  if (!pet) notFound();

  const mapsLink = `https://www.google.com/maps?q=${pet.last_seen_lat},${pet.last_seen_lng}`;

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Mascotas Perdidas', url: 'https://bigotesypaticas.com/mascotas-perdidas' },
          { name: pet.pet_name, url: `https://bigotesypaticas.com/mascotas-perdidas/${pet.id}` },
        ]}
      />

      <div className="container-wide py-10 max-w-3xl">
        <Link href="/mascotas-perdidas" className="inline-flex items-center gap-1 text-sm text-muted-foreground mb-6 hover:text-foreground">
          <ChevronLeft className="h-4 w-4" /> Volver a mascotas perdidas
        </Link>

        <div className="rounded-3xl overflow-hidden border border-border bg-card">
          {pet.photos[0] ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={pet.photos[0]} alt={pet.pet_name} className="w-full h-80 object-cover" />
          ) : (
            <div className="w-full h-80 bg-gradient-to-br from-[#e8433a] to-[#c62f28] flex items-center justify-center text-8xl">🐾</div>
          )}

          <div className="p-8">
            <div className="flex items-center gap-2 mb-2">
              <h1 className="text-3xl font-display font-extrabold">{pet.pet_name}</h1>
              <span className="text-[10px] font-bold uppercase tracking-wide text-[#c62f28] bg-[#FDEEE9] px-2 py-0.5 rounded-full">
                Perdido
              </span>
            </div>
            <p className="text-muted-foreground capitalize mb-6">
              {pet.species}{pet.breed ? ` · ${pet.breed}` : ''} · {pet.color}
            </p>

            {pet.reward != null && pet.reward > 0 && (
              <div className="inline-flex items-center gap-2 rounded-xl bg-emerald-50 text-emerald-700 px-4 py-2 text-sm font-semibold mb-6">
                <Gift className="h-4 w-4" /> Recompensa por su regreso: ${pet.reward.toLocaleString('es-CO')}
              </div>
            )}

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
          </div>
        </div>

        <div className="mt-8 rounded-2xl bg-[#f5f0e8] p-6 text-center">
          <p className="text-sm text-gray-600">
            ¿Encontraste una mascota y no sabes de quién es?{' '}
            <Link href="/mascotas-encontradas" className="font-semibold text-[#187f77]">
              Publícala aquí
            </Link>
            .
          </p>
        </div>
      </div>
    </>
  );
}
