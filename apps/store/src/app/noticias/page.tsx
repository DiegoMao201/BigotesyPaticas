import type { Metadata } from 'next';
import Link from 'next/link';
import Image from 'next/image';
import { storeApi } from '@/lib/api';
import { BreadcrumbSchema, ItemListSchema } from '@/components/seo/JsonLd';
import { Calendar, Newspaper } from 'lucide-react';

// 15 min: una noticia recién publicada tiene que aparecer rápido, que es de lo
// que vive esta sección. El blog puede esperar media hora, esto no.
export const revalidate = 900;

export const metadata: Metadata = {
  title: 'Noticias de interés para dueños de perros y gatos en Colombia',
  description:
    'Leyes, derechos, deberes, estudios y novedades reales sobre perros y gatos en Colombia. Verificadas y con la fuente a la vista, explicadas para dueños de Pereira y Dosquebradas.',
  keywords: [
    'noticias mascotas Colombia',
    'leyes animales Colombia',
    'derechos de los animales',
    'normas para perros Colombia',
    'noticias perros y gatos',
    'bienestar animal Pereira',
  ],
  alternates: { canonical: 'https://bigotesypaticas.com/noticias' },
  openGraph: {
    title: 'Noticias de interés — Bigotes y Paticas',
    description: 'Leyes, estudios y novedades reales sobre perros y gatos en Colombia, con la fuente siempre a la vista.',
    url: 'https://bigotesypaticas.com/noticias',
  },
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('es-CO', {
    year: 'numeric', month: 'long', day: 'numeric',
  });
}

export default async function NoticiasPage() {
  const data = await storeApi.newsList({ per_page: 30 });
  const posts = data.posts;

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Noticias de interés', url: 'https://bigotesypaticas.com/noticias' },
        ]}
      />
      {posts.length > 0 && (
        <ItemListSchema
          name="Noticias de interés para dueños de perros y gatos en Colombia"
          url="https://bigotesypaticas.com/noticias"
          items={posts.map((p) => ({
            name: p.title,
            url: `https://bigotesypaticas.com/noticias/${p.slug}`,
          }))}
        />
      )}

      <div className="container-wide py-12">
        <div className="max-w-2xl mb-12">
          <div className="flex items-center gap-2 mb-3">
            <Newspaper className="h-5 w-5 text-brand-500" />
            <span className="text-sm font-semibold text-brand-600 uppercase tracking-wide">
              Noticias de interés
            </span>
          </div>
          <h1 className="text-3xl md:text-4xl font-display font-extrabold leading-tight mb-4 text-[#0d4a45]">
            Lo que sí deberías saber si tienes perro o gato en Colombia
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed">
            Leyes, derechos, deberes, estudios y novedades reales. Cada nota lleva la fuente
            para que la verifiques tú mismo. Nada de rumores de cadena de WhatsApp.
          </p>
        </div>

        {posts.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-border p-12 text-center">
            <div className="text-4xl mb-3">📰</div>
            <p className="text-muted-foreground">
              Todavía no hay noticias publicadas. Vuelve pronto.
            </p>
          </div>
        ) : (
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {posts.map((post) => (
              <Link
                key={post.id}
                href={`/noticias/${post.slug}`}
                className="group flex flex-col rounded-3xl border border-border overflow-hidden hover:shadow-lg transition-shadow bg-white"
              >
                <div className="relative aspect-video bg-teal-50">
                  {post.cover_image_url ? (
                    <Image
                      src={post.cover_image_url}
                      alt={post.title}
                      fill
                      sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                      className="object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-4xl">🐾</div>
                  )}
                </div>
                <div className="flex flex-1 flex-col p-5">
                  {post.source_name && (
                    <span className="text-xs font-semibold text-brand-600 uppercase tracking-wide mb-2">
                      {post.source_name}
                    </span>
                  )}
                  <h2 className="font-display font-bold text-lg leading-snug text-[#0d4a45] mb-2 group-hover:text-teal-700 transition-colors">
                    {post.title}
                  </h2>
                  {post.excerpt && (
                    <p className="text-sm text-muted-foreground leading-relaxed line-clamp-3 flex-1">
                      {post.excerpt}
                    </p>
                  )}
                  {post.published_at && (
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-4">
                      <Calendar className="h-3.5 w-3.5" />
                      {formatDate(post.published_at)}
                    </div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
