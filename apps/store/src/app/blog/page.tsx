import type { Metadata } from 'next';
import Link from 'next/link';
import { storeApi } from '@/lib/api';
import { BreadcrumbSchema } from '@/components/seo/JsonLd';
import { Calendar, Tag } from 'lucide-react';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Blog de mascotas — Consejos y guías para perros y gatos en Pereira',
  description:
    'Artículos sobre cuidado, nutrición y salud para mascotas. Guías veterinarias y consejos para dueños de perros y gatos en Pereira y Dosquebradas, Risaralda.',
  keywords: [
    'cuidado mascotas Pereira',
    'blog mascotas Colombia',
    'guía nutrición perros',
    'salud gatos Dosquebradas',
    'consejos veterinarios',
  ],
  alternates: { canonical: 'https://bigotesypaticas.com/blog' },
  openGraph: {
    title: 'Blog de mascotas — Bigotes y Paticas',
    description: 'Consejos veterinarios y guías de cuidado para perros y gatos en Pereira y Dosquebradas.',
    url: 'https://bigotesypaticas.com/blog',
  },
};

const CATEGORY_LABELS: Record<string, string> = {
  nutricion: '🥩 Nutrición',
  salud: '💊 Salud',
  cuidado: '✂️ Cuidado',
  razas: '🐕 Razas',
  comportamiento: '🧠 Comportamiento',
  local: '📍 Pereira',
  general: '📝 General',
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('es-CO', {
    year: 'numeric', month: 'long', day: 'numeric',
  });
}

export default async function BlogPage() {
  const data = await storeApi.blogList({ per_page: 30 });
  const posts = data.posts;

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Blog', url: 'https://bigotesypaticas.com/blog' },
        ]}
      />

      <div className="container-wide py-12">
        {/* Header */}
        <div className="max-w-2xl mb-12">
          <p className="text-brand-600 font-semibold text-sm mb-2 uppercase tracking-wider">Blog</p>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold mb-4 text-[#0d4a45]">
            Consejos para tu mascota
          </h1>
          <p className="text-muted-foreground text-lg">
            Guías de nutrición, salud y cuidado escritas por veterinarios. Todo lo que necesitas
            saber para que tu perro o gato viva feliz en Pereira y Dosquebradas.
          </p>
        </div>

        {posts.length === 0 ? (
          <div className="text-center py-24">
            <div className="text-7xl mb-6">📝</div>
            <h2 className="text-2xl font-display font-bold mb-3">Blog próximamente</h2>
            <p className="text-muted-foreground max-w-sm mx-auto">
              Estamos preparando artículos con consejos veterinarios para tu mascota.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {posts.map((post) => (
              <Link
                key={post.id}
                href={`/blog/${post.slug}`}
                className="group block rounded-3xl border border-border bg-card overflow-hidden hover:shadow-lg hover:-translate-y-1 transition-all duration-300"
              >
                {post.cover_image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={post.cover_image_url}
                    alt={post.title}
                    className="w-full h-48 object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                ) : (
                  <div className="w-full h-48 bg-gradient-to-br from-teal-600 to-teal-900 flex items-center justify-center text-6xl">
                    🐾
                  </div>
                )}

                <div className="p-6">
                  {post.category && (
                    <div className="flex items-center gap-1.5 mb-3">
                      <Tag className="h-3 w-3 text-brand-500" />
                      <span className="text-xs font-semibold text-brand-600 uppercase tracking-wide">
                        {CATEGORY_LABELS[post.category] ?? post.category}
                      </span>
                    </div>
                  )}

                  <h2 className="font-display font-bold text-xl leading-snug mb-3 group-hover:text-teal-700 transition-colors line-clamp-2">
                    {post.title}
                  </h2>

                  {post.excerpt && (
                    <p className="text-muted-foreground text-sm leading-relaxed line-clamp-3 mb-4">
                      {post.excerpt}
                    </p>
                  )}

                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Calendar className="h-3 w-3" />
                    {post.published_at && formatDate(post.published_at)}
                    <span>·</span>
                    <span>{post.author}</span>
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
