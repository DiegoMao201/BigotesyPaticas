import type { Metadata } from 'next';
import Link from 'next/link';
import Image from 'next/image';
import { notFound } from 'next/navigation';
import { storeApi } from '@/lib/api';
import { BreadcrumbSchema, NewsArticleSchema } from '@/components/seo/JsonLd';
import { Calendar, ArrowLeft, ExternalLink } from 'lucide-react';

export const revalidate = 900;

interface Props { params: { slug: string } }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const post = await storeApi.newsBySlug(params.slug);
  if (!post) return { title: 'Noticia no encontrada | Bigotes y Paticas' };

  const url = `https://bigotesypaticas.com/noticias/${post.slug}`;
  return {
    title: post.meta_title || `${post.title} | Bigotes y Paticas`,
    description: post.meta_description || post.excerpt || '',
    keywords: post.keywords,
    // canónica en /noticias y no en /blog: la nota vive en las dos tablas pero en
    // una sola sección, y repetir la URL la haría competir consigo misma.
    alternates: { canonical: url },
    openGraph: {
      title: post.title,
      description: post.meta_description || post.excerpt || '',
      url,
      type: 'article',
      publishedTime: post.published_at || undefined,
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

export default async function NoticiaPage({ params }: Props) {
  const post = await storeApi.newsBySlug(params.slug);
  if (!post) notFound();

  const url = `https://bigotesypaticas.com/noticias/${post.slug}`;

  return (
    <>
      <NewsArticleSchema post={post} url={url} />
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Noticias de interés', url: 'https://bigotesypaticas.com/noticias' },
          { name: post.title, url },
        ]}
      />

      <div className="container-tight py-12">
        <Link
          href="/noticias"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-teal-700 mb-8 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Volver a noticias
        </Link>

        <header className="mb-10">
          <span className="text-sm font-semibold text-brand-600 uppercase tracking-wide">
            📰 Noticia de interés
          </span>

          <h1 className="text-3xl md:text-4xl font-display font-extrabold leading-tight mb-4 mt-3 text-[#0d4a45]">
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

        {/* El video vertical que ya salió en redes. Va antes del texto porque es
            lo que la gente reconoce y lo que la retiene en la página. */}
        {post.video_url ? (
          <div className="mx-auto mb-10 w-full max-w-[340px] overflow-hidden rounded-3xl shadow-sm bg-black">
            <video
              src={post.video_url}
              poster={post.cover_image_url || undefined}
              controls
              playsInline
              preload="metadata"
              className="h-auto w-full"
            />
          </div>
        ) : post.cover_image_url ? (
          <div className="relative mb-10 aspect-video w-full overflow-hidden rounded-3xl shadow-sm">
            <Image
              src={post.cover_image_url}
              alt={post.title}
              fill
              priority
              sizes="(max-width: 768px) 100vw, 768px"
              className="object-cover"
            />
          </div>
        ) : null}

        <div
          className="blog-content"
          dangerouslySetInnerHTML={{ __html: post.content ?? '' }}
        />

        {/* La fuente es la razón por la que esto informa en vez de desinformar.
            Va visible y enlazada, no escondida al final en letra chiquita. */}
        {post.source_url && (
          <div className="mt-10 rounded-2xl border border-teal-100 bg-teal-50 p-5">
            <p className="text-sm text-teal-900">
              <strong>Verifícalo tú mismo.</strong> Esta nota se basa en información publicada
              {post.source_name ? ` por ${post.source_name}` : ''}.
            </p>
            <a
              href={post.source_url}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="mt-2 inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 hover:text-teal-900 underline underline-offset-4"
            >
              Ver la fuente original <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        )}

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

        <div className="mt-12 rounded-3xl bg-gradient-to-br from-teal-600 to-teal-900 text-white p-8 text-center">
          <div className="text-4xl mb-3">🐾</div>
          <h3 className="font-display font-bold text-2xl mb-2">
            ¿Tienes perro o gato en Pereira o Dosquebradas?
          </h3>
          <p className="text-teal-200 mb-6">
            Alimento, grooming, consulta veterinaria y vacunación con carnet. Domicilio gratis
            desde $30.000.
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
