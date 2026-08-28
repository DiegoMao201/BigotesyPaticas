import type { Metadata } from 'next';
import Link from 'next/link';
import { storeApi } from '@/lib/api';
import { BreadcrumbSchema } from '@/components/seo/JsonLd';
import { Gift } from 'lucide-react';

export const revalidate = 300; // 5 min -- son reportes urgentes, se refrescan seguido

export const metadata: Metadata = {
  title: 'Mascotas Perdidas en Pereira y Dosquebradas — Bigotes y Paticas',
  description:
    'Reportes reales de perros y gatos perdidos en Pereira y Dosquebradas. Ayuda a la comunidad a encontrarlos, o reporta la tuya.',
  keywords: [
    'mascota perdida Pereira',
    'perro perdido Dosquebradas',
    'gato perdido Pereira',
    'ayuda mascota perdida Risaralda',
  ],
  alternates: { canonical: 'https://bigotesypaticas.com/mascotas-perdidas' },
  openGraph: {
    title: 'Mascotas Perdidas en Pereira y Dosquebradas',
    description: 'Reportes reales de la comunidad. Ayuda a que vuelvan a casa.',
    url: 'https://bigotesypaticas.com/mascotas-perdidas',
  },
};

function timeAgo(iso: string) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days < 1) return 'hoy';
  if (days === 1) return 'ayer';
  return `hace ${days} días`;
}

export default async function MascotasPerdidasPage() {
  const pets = await storeApi.lostPets();

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Mascotas Perdidas', url: 'https://bigotesypaticas.com/mascotas-perdidas' },
        ]}
      />

      <div className="bg-gradient-to-b from-[#c62f28] to-[#e8433a] text-white py-16 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-3xl md:text-5xl font-display font-extrabold mb-4 leading-tight">
            Mascotas Perdidas en Pereira y Dosquebradas
          </h1>
          <p className="text-white/85 max-w-xl mx-auto">
            Reportes reales publicados por la comunidad desde el portal de Bigotes y Paticas. Compártelos, y si ves
            alguno, escríbele directo a su familia.
          </p>
          <Link
            href="https://mi.bigotesypaticas.com/sos/new"
            className="inline-flex items-center gap-2 mt-6 px-6 py-3 bg-white text-[#c62f28] rounded-xl font-bold text-sm hover:bg-white/90 transition-colors"
          >
            🐾 Reportar mi mascota perdida
          </Link>
        </div>
      </div>

      <div className="container-wide py-12">
        {pets.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-6xl mb-5">🎉</div>
            <h2 className="text-2xl font-display font-bold mb-2">No hay reportes activos ahora mismo</h2>
            <p className="text-muted-foreground">Buena señal — significa que todos están en casa.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {pets.map((pet) => (
              <Link
                key={pet.id}
                href={`/mascotas-perdidas/${pet.id}`}
                className="group block rounded-3xl border border-border bg-card overflow-hidden hover:shadow-lg hover:-translate-y-1 transition-all duration-300"
              >
                {pet.photos[0] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={pet.photos[0]}
                    alt={pet.pet_name}
                    loading="lazy"
                    className="w-full h-48 object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                ) : (
                  <div className="w-full h-48 bg-gradient-to-br from-[#e8433a] to-[#c62f28] flex items-center justify-center text-6xl">
                    🐾
                  </div>
                )}
                <div className="p-5">
                  <div className="flex items-center gap-2 mb-2">
                    <h2 className="font-display font-bold text-lg">{pet.pet_name}</h2>
                    <span className="text-[10px] font-bold uppercase tracking-wide text-[#c62f28] bg-[#FDEEE9] px-2 py-0.5 rounded-full">
                      Perdido
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground capitalize mb-3">
                    {pet.species}{pet.breed ? ` · ${pet.breed}` : ''} · {pet.color}
                  </p>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
                    <span>{timeAgo(pet.created_at)}</span>
                    {pet.reward != null && pet.reward > 0 && (
                      <span className="inline-flex items-center gap-1 font-semibold text-emerald-700">
                        <Gift className="h-3 w-3" /> Recompensa
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
