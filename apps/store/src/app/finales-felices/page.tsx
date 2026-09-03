import type { Metadata } from 'next';
import Link from 'next/link';
import { storeApi } from '@/lib/api';
import { BreadcrumbSchema, ItemListSchema } from '@/components/seo/JsonLd';
import { SuccessStoryCard, SUCCESS_BADGE } from '@/components/community/SuccessStoryCard';

export const revalidate = 300;

export const metadata: Metadata = {
  title: 'Finales Felices — Mascotas que volvieron a casa y fueron adoptadas en Pereira y Dosquebradas',
  description:
    'Historias reales de la comunidad de Bigotes y Paticas: mascotas perdidas que ya están en casa, animales rescatados que se reunieron con su familia y peluditos que encontraron hogar en Pereira y Dosquebradas.',
  keywords: [
    'mascota encontrada Pereira',
    'perro volvio a casa Pereira',
    'gato encontrado Dosquebradas',
    'adopcion exitosa Pereira',
    'historias de adopcion Risaralda',
    'reencuentro mascota Pereira',
  ],
  alternates: { canonical: 'https://bigotesypaticas.com/finales-felices' },
  openGraph: {
    title: 'Finales Felices — comunidad Bigotes y Paticas',
    description: 'Mascotas que volvieron a casa, se reunieron con su familia o encontraron hogar en Pereira y Dosquebradas.',
    url: 'https://bigotesypaticas.com/finales-felices',
  },
};

export default async function FinalesFelicesPage() {
  const stories = await storeApi.successStories(60);

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Finales Felices', url: 'https://bigotesypaticas.com/finales-felices' },
        ]}
      />
      <ItemListSchema
        name="Finales felices de la comunidad Bigotes y Paticas"
        url="https://bigotesypaticas.com/finales-felices"
        items={stories.map((s) => ({ name: `${s.headline} ${s.title}`, url: `https://bigotesypaticas.com${s.path}` }))}
      />

      <div className="bg-gradient-to-b from-emerald-700 to-emerald-500 text-white py-16 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <div className="text-5xl mb-4">🎉</div>
          <h1 className="text-3xl md:text-5xl font-display font-extrabold mb-4 leading-tight">Finales Felices</h1>
          <p className="text-white/90 max-w-xl mx-auto">
            Mascotas que volvieron a casa, animales rescatados que se reunieron con su familia y peluditos que encontraron
            hogar. Todo gracias a la comunidad de Pereira y Dosquebradas que comparte, avisa y ayuda.
          </p>
        </div>
      </div>

      <div className="container-wide py-12">
        {stories.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-6xl mb-5">🐾</div>
            <h2 className="text-2xl font-display font-bold mb-2">Pronto habrá historias aquí</h2>
            <p className="text-muted-foreground">
              Cada vez que una mascota vuelve a casa o encuentra hogar, la celebramos en esta página durante 30 días.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {stories.map((s) => (
              <SuccessStoryCard
                key={`${s.type}-${s.id}`}
                href={s.path}
                photo={s.photo}
                title={s.title}
                subtitle={s.subtitle}
                headline={s.headline}
                note={s.note}
                badge={SUCCESS_BADGE[s.type] ?? 'Final feliz'}
                date={s.resolved_at}
              />
            ))}
          </div>
        )}
      </div>

      <div className="bg-[#f5f0e8] py-14 px-4">
        <div className="max-w-2xl mx-auto text-center space-y-3">
          <h2 className="text-xl font-display font-bold text-[#0d4a45]">¿Quieres ser parte del próximo final feliz?</h2>
          <p className="text-sm text-gray-600 leading-relaxed">
            Revisa las <Link href="/mascotas-perdidas" className="font-semibold text-[#c62f28]">mascotas perdidas</Link>, los{' '}
            <Link href="/mascotas-encontradas" className="font-semibold text-[#187f77]">animales encontrados</Link> o el{' '}
            <Link href="/adopcion" className="font-semibold text-[#187f77]">foro de adopción</Link>. Compartir una publicación
            también ayuda.
          </p>
        </div>
      </div>
    </>
  );
}
