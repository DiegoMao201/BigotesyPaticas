import type { Metadata } from 'next';
import Link from 'next/link';
import { storeApi } from '@/lib/api';
import { BreadcrumbSchema } from '@/components/seo/JsonLd';
import { PawPrint } from 'lucide-react';

export const revalidate = 300;

export const metadata: Metadata = {
  title: 'Animales Encontrados en Pereira y Dosquebradas — Bigotes y Paticas',
  description:
    'Perros y gatos que fueron encontrados o rescatados en Pereira y Dosquebradas y están a salvo, esperando que su familia los reconozca.',
  keywords: [
    'perro encontrado Pereira',
    'gato encontrado Dosquebradas',
    'animal rescatado Risaralda',
    'mascota encontrada Pereira',
  ],
  alternates: { canonical: 'https://bigotesypaticas.com/mascotas-encontradas' },
  openGraph: {
    title: 'Animales Encontrados en Pereira y Dosquebradas',
    description: 'Animales rescatados, a salvo, esperando a su familia.',
    url: 'https://bigotesypaticas.com/mascotas-encontradas',
  },
};

function timeAgo(iso: string) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days < 1) return 'hoy';
  if (days === 1) return 'ayer';
  return `hace ${days} días`;
}

export default async function MascotasEncontradasPage() {
  const events = await storeApi.foundAnimals();

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Animales Encontrados', url: 'https://bigotesypaticas.com/mascotas-encontradas' },
        ]}
      />

      <div className="bg-gradient-to-b from-[#085041] to-[#187f77] text-white py-16 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-3xl md:text-5xl font-display font-extrabold mb-4 leading-tight">
            Animales Encontrados en Pereira y Dosquebradas
          </h1>
          <p className="text-white/85 max-w-xl mx-auto">
            Animales rescatados que están a salvo, publicados por la comunidad de Bigotes y Paticas. Revisa las
            fotos — puede que reconozcas a tu mascota.
          </p>
          <Link
            href="https://mi.bigotesypaticas.com/sos/encontrados/reportar"
            className="inline-flex items-center gap-2 mt-6 px-6 py-3 bg-white text-[#0d4a45] rounded-xl font-bold text-sm hover:bg-white/90 transition-colors"
          >
            🏠 Reportar un animalito encontrado
          </Link>
        </div>
      </div>

      <div className="container-wide py-12">
        {events.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-6xl mb-5">🏠</div>
            <h2 className="text-2xl font-display font-bold mb-2">No hay animalitos encontrados por ahora</h2>
            <p className="text-muted-foreground">¿Encontraste alguno? Sé el primero en reportarlo.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {events.map((ev) => (
              <Link
                key={ev.id}
                href={`/mascotas-encontradas/${ev.id}`}
                className="group block rounded-3xl border border-border bg-card overflow-hidden hover:shadow-lg hover:-translate-y-1 transition-all duration-300"
              >
                {ev.cover_thumb_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={ev.cover_thumb_url}
                    alt={ev.title}
                    loading="lazy"
                    className="w-full h-48 object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                ) : (
                  <div className="w-full h-48 bg-gradient-to-br from-[#187f77] to-[#085041] flex items-center justify-center text-6xl">
                    <PawPrint className="h-12 w-12 text-white/70" />
                  </div>
                )}
                <div className="p-5">
                  <div className="flex items-center gap-2 mb-2">
                    <h2 className="font-display font-bold text-lg line-clamp-1">{ev.title}</h2>
                    <span className="shrink-0 text-[10px] font-bold uppercase tracking-wide text-emerald-800 bg-[#E6F5F1] px-2 py-0.5 rounded-full">
                      🐾 {ev.animal_count}
                    </span>
                  </div>
                  {ev.address && <p className="text-sm text-muted-foreground mb-3 line-clamp-1">{ev.address}</p>}
                  <span className="text-xs text-muted-foreground">{timeAgo(ev.found_at)}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
