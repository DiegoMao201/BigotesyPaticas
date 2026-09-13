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

      <div className="container-wide py-12">
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

        {/* DOS COLUMNAS en escritorio: el video vertical a la izquierda, pegado
            mientras se baja, y el texto arrancando a su derecha. En una sola
            columna el video de 9:16 dejaba dos franjas blancas enormes a los
            lados (Diego: "se ve muy mal esos espacios en blanco"). En celular
            se apilan, que es como se lee de verdad. */}
        <div className="grid gap-10 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)] lg:gap-14">
          <div className="lg:sticky lg:top-24 lg:self-start">
            {post.video_url ? (
              <div className="mx-auto w-full max-w-[340px] overflow-hidden rounded-3xl bg-black shadow-sm">
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
              <div className="relative mx-auto aspect-[9/16] w-full max-w-[340px] overflow-hidden rounded-3xl shadow-sm">
                <Image
                  src={post.cover_image_url}
                  alt={post.title}
                  fill
                  priority
                  sizes="(max-width: 1024px) 100vw, 340px"
                  className="object-cover"
                />
              </div>
            ) : null}

            {/* La fuente va junto al video, no perdida al final: es lo que hace
                que esto informe en vez de desinformar. */}
            {post.source_url && (
              <div className="mt-6 rounded-2xl border border-teal-100 bg-teal-50 p-5">
                <p className="text-sm text-teal-900">
                  <strong>Verifícalo tú mismo.</strong> Esta nota se basa en información publicada
                  {post.source_name ? ` por ${post.source_name}` : ''}.
                </p>
                <a
                  href={post.source_url}
                  target="_blank"
                  rel="noopener noreferrer nofollow"
                  className="mt-2 inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 underline underline-offset-4 hover:text-teal-900"
                >
                  Ver la fuente original <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
            )}
          </div>

          <div className="min-w-0">
            <div
              className="blog-content"
              dangerouslySetInnerHTML={{ __html: post.content ?? '' }}
            />

            {post.keywords.length > 0 && (
              <div className="mt-10 flex flex-wrap gap-2 border-t border-border pt-8">
                {post.keywords.map((kw) => (
                  <span
                    key={kw}
                    className="rounded-full border border-teal-100 bg-teal-50 px-3 py-1.5 text-xs font-medium text-teal-700"
                  >
                    #{kw}
                  </span>
                ))}
              </div>
            )}

            <div className="mt-12 rounded-3xl bg-gradient-to-br from-teal-600 to-teal-900 p-8 text-center text-white">
              <div className="mb-3 text-4xl">🐾</div>
              <h3 className="mb-2 font-display text-2xl font-bold">
                ¿Tienes perro o gato en Pereira o Dosquebradas?
              </h3>
              <p className="mb-6 text-teal-200">
                Alimento, grooming, consulta veterinaria y vacunación con carnet. Domicilio gratis
                desde $30.000.
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                <Link
                  href="/categorias/todos"
                  className="rounded-full bg-[#f5a641] px-6 py-3 font-bold text-[#0d4a45] transition-colors hover:bg-amber-300"
                >
                  Ver catálogo →
                </Link>
                <a
                  href="https://wa.me/573206876633"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-full bg-green-500 px-6 py-3 font-semibold text-white transition-colors hover:bg-green-400"
                >
                  💬 WhatsApp
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
