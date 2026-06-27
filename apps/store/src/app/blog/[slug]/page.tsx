import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { storeApi } from '@/lib/api';
import { ArticleSchema, BreadcrumbSchema } from '@/components/seo/JsonLd';
import { Calendar, ArrowLeft, Tag } from 'lucide-react';

export const dynamic = 'force-dynamic';

interface Props { params: { slug: string } }

const CATEGORY_LABELS: Record<string, string> = {
  nutricion: '🥩 Nutrición',
  salud: '💊 Salud',
  cuidado: '✂️ Cuidado',
  razas: '🐕 Razas',
  comportamiento: '🧠 Comportamiento',
  local: '📍 Pereira',
  general: '📝 General',
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const post = await storeApi.blogBySlug(params.slug);
  if (!post) return { title: 'Artículo no encontrado | Bigotes y Paticas' };

  return {
    title: post.meta_title || `${post.title} | Bigotes y Paticas`,
    description: post.meta_description || post.excerpt || '',
    keywords: post.keywords,
    alternates: { canonical: `https://bigotesypaticas.com/blog/${post.slug}` },
    openGraph: {
      title: post.title,
      description: post.meta_description || post.excerpt || '',
      url: `https://bigotesypaticas.com/blog/${post.slug}`,
      type: 'article',
      ...(post.cover_image_url && {
        images: [{ url: post.cover_image_url, width: 1200, height: 630, alt: post.title }],
      }),
    },
  };
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('es-CO', {
    year: 'numeric', month: 'long', day: 'numeric',
  });
}

export default async function BlogPostPage({ params }: Props) {
  const post = await storeApi.blogBySlug(params.slug);
  if (!post) notFound();

  const postUrl = `https://bigotesypaticas.com/blog/${post.slug}`;

  return (
    <>
      <ArticleSchema
        title={post.title}
        description={post.meta_description || post.excerpt || undefined}
        imageUrl={post.cover_image_url || undefined}
        publishedAt={post.published_at || undefined}
        updatedAt={post.updated_at || undefined}
        author={post.author}
        url={postUrl}
      />
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Blog', url: 'https://bigotesypaticas.com/blog' },
          { name: post.title, url: postUrl },
        ]}
      />

      <div className="container-tight py-12">
        {/* Back */}
        <Link
          href="/blog"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-teal-700 mb-8 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Volver al blog
        </Link>

        {/* Header */}
        <header className="mb-10">
          {post.category && (
            <div className="flex items-center gap-1.5 mb-4">
              <Tag className="h-3.5 w-3.5 text-brand-500" />
              <span className="text-sm font-semibold text-brand-600 uppercase tracking-wide">
                {CATEGORY_LABELS[post.category] ?? post.category}
              </span>
            </div>
          )}

          <h1 className="text-3xl md:text-4xl font-display font-extrabold leading-tight mb-4 text-[#0d4a45]">
            {post.title}
          </h1>

          {post.excerpt && (
            <p className="text-xl text-muted-foreground leading-relaxed mb-5">{post.excerpt}</p>
          )}

          <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground border-b border-border pb-6">
            <div className="flex items-center gap-1.5">
              <Calendar className="h-4 w-4" />
              {post.published_at && formatDate(post.published_at)}
            </div>
            <span>·</span>
            <span>{post.author}</span>
          </div>
        </header>

        {/* Cover */}
        {post.cover_image_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={post.cover_image_url}
            alt={post.title}
            className="w-full rounded-3xl aspect-video object-cover mb-10 shadow-sm"
          />
        )}

        {/* Content */}
        <div
          className="blog-content"
          dangerouslySetInnerHTML={{ __html: post.content }}
        />

        {/* Keywords */}
        {post.keywords.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-10 pt-8 border-t border-border">
            {post.keywords.map((kw) => (
              <span
                key={kw}
                className="px-3 py-1.5 text-xs rounded-full bg-teal-50 border border-teal-100 text-teal-700 font-medium"
              >
                #{kw}
              </span>
            ))}
          </div>
        )}

        {/* CTA */}
        <div className="mt-12 rounded-3xl bg-gradient-to-br from-teal-600 to-teal-900 text-white p-8 text-center">
          <div className="text-4xl mb-3">🐾</div>
          <h3 className="font-display font-bold text-2xl mb-2">
            En Bigotes y Paticas tenemos lo que necesitas
          </h3>
          <p className="text-teal-200 mb-6">
            Productos premium para tu mascota con entrega en 24-72h en Pereira y Dosquebradas.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/categorias/todos"
              className="px-6 py-3 rounded-full bg-[#f5a641] text-[#0d4a45] font-bold hover:bg-amber-300 transition-colors"
            >
              Ver catálogo →
            </Link>
            <a
              href="https://wa.me/573206876633"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 rounded-full bg-green-500 text-white font-semibold hover:bg-green-400 transition-colors"
            >
              💬 WhatsApp
            </a>
          </div>
        </div>
      </div>
    </>
  );
}
