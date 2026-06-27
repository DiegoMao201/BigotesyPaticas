import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { storeApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { BreadcrumbSchema } from '@/components/seo/JsonLd';
import { MapPin, Truck, ChevronRight } from 'lucide-react';

export const dynamic = 'force-dynamic';

interface Props { params: { slug: string } }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const landing = await storeApi.landingBySlug(params.slug);
  if (!landing) return { title: 'Página no encontrada | Bigotes y Paticas' };

  return {
    title: `${landing.title} | Bigotes y Paticas`,
    description: landing.meta_description ?? undefined,
    alternates: { canonical: `https://bigotesypaticas.com/landing/${landing.slug}` },
    openGraph: {
      title: landing.title,
      description: landing.meta_description ?? undefined,
      url: `https://bigotesypaticas.com/landing/${landing.slug}`,
    },
  };
}

export default async function LandingPage({ params }: Props) {
  const landing = await storeApi.landingBySlug(params.slug);
  if (!landing) notFound();

  const products = landing.category_slug
    ? await storeApi.list({ category_slug: landing.category_slug, per_page: 8 })
    : { items: [], total: 0, page: 1, per_page: 8 };

  const pageUrl = `https://bigotesypaticas.com/landing/${landing.slug}`;

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: landing.h1, url: pageUrl },
        ]}
      />

      {/* Hero */}
      <header className="py-14 text-center bg-gradient-to-b from-teal-50/60 to-transparent border-b border-border/40">
        <div className="container-tight">
          {landing.geographic_focus && (
            <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-700 bg-teal-50 border border-teal-100 rounded-full px-3 py-1.5 mb-4">
              <MapPin className="h-3 w-3" />
              {landing.geographic_focus}
            </div>
          )}
          <h1 className="text-4xl md:text-5xl font-display font-extrabold text-[#0d4a45] leading-tight mb-4">
            {landing.h1}
          </h1>
          {landing.geographic_focus && (
            <p className="text-muted-foreground text-lg">
              Entrega a domicilio en {landing.geographic_focus} en 24-72 horas
            </p>
          )}
        </div>
      </header>

      {/* Breadcrumb */}
      <div className="container-tight py-3">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Link href="/" className="hover:text-teal-700 transition-colors">Inicio</Link>
          <ChevronRight className="h-3 w-3" />
          <span>{landing.h1}</span>
        </div>
      </div>

      {/* Intro content */}
      {landing.intro_content && (
        <div
          className="container-tight py-8 prose prose-lg max-w-3xl mx-auto
                     prose-headings:text-[#0d4a45] prose-a:text-teal-700
                     prose-strong:text-foreground"
          dangerouslySetInnerHTML={{ __html: landing.intro_content }}
        />
      )}

      {/* Badges de confianza */}
      <div className="container-tight py-6">
        <div className="flex flex-wrap gap-3 justify-center text-sm">
          {[
            '✓ Más de 900 productos',
            '✓ Envío 24-72h',
            '✓ Marcas premium: Hills, Royal Canin, Pro Plan',
            '✓ Pago contra entrega disponible',
          ].map((b) => (
            <span key={b} className="px-4 py-2 rounded-full border border-teal-100 bg-teal-50 text-teal-700 font-medium">
              {b}
            </span>
          ))}
        </div>
      </div>

      {/* Productos relacionados */}
      {products.items.length > 0 && (
        <section className="container-wide py-12">
          <div className="mb-6">
            <p className="text-teal-600 font-semibold text-sm mb-1">Catálogo</p>
            <h2 className="text-2xl md:text-3xl font-display font-bold text-[#0d4a45]">
              Productos recomendados
            </h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-5">
            {products.items.map((p) => {
              const disc =
                p.compare_at_price && Number(p.compare_at_price) > Number(p.price)
                  ? Math.round((1 - Number(p.price) / Number(p.compare_at_price)) * 100)
                  : null;
              return (
                <Link
                  key={p.id}
                  href={`/producto/${p.slug}`}
                  className="group rounded-3xl border border-border bg-card overflow-hidden hover:shadow-warm hover:-translate-y-1 transition-all duration-300"
                >
                  <div className="aspect-square bg-white flex items-center justify-center p-3 relative">
                    {p.primary_image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={p.primary_image_url}
                        alt={p.name}
                        className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-300"
                      />
                    ) : (
                      <div className="text-5xl">🐾</div>
                    )}
                    {disc && (
                      <div className="absolute top-2 right-2 text-xs font-bold px-2 py-0.5 rounded-full bg-teal-600 text-white">
                        -{disc}%
                      </div>
                    )}
                  </div>
                  <div className="p-4">
                    <h3 className="text-sm font-semibold line-clamp-2 group-hover:text-teal-700 transition-colors">
                      {p.name}
                    </h3>
                    <div className="flex items-baseline gap-2 mt-2">
                      <span className="font-extrabold text-teal-700 text-sm">
                        {formatCurrency(p.price)}
                      </span>
                      {disc && p.compare_at_price && (
                        <span className="text-xs text-muted-foreground line-through">
                          {formatCurrency(p.compare_at_price)}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
          {landing.category_slug && (
            <div className="text-center mt-8">
              <Link
                href={`/categorias/${landing.category_slug}`}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-full border-2 border-teal-600 text-teal-700 font-semibold hover:bg-teal-50 transition-colors"
              >
                Ver todo el catálogo <ChevronRight className="h-4 w-4" />
              </Link>
            </div>
          )}
        </section>
      )}

      {/* CTA final */}
      <section className="bg-gradient-to-br from-teal-600 to-teal-900 text-white py-16 px-6 text-center mt-12">
        <div className="container-tight">
          <div className="text-5xl mb-4">🐾</div>
          <h2 className="text-3xl md:text-4xl font-display font-bold mb-3">
            {landing.cta_text ?? '¿Listo para pedir?'}
          </h2>
          <p className="text-teal-200 text-lg mb-8 max-w-xl mx-auto">
            Entrega a domicilio en 24-72h en Pereira y Dosquebradas. Pago contra entrega disponible.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href="/categorias/todos"
              className="px-7 py-3.5 rounded-full bg-[#f5a641] text-[#0d4a45] font-bold text-lg hover:bg-amber-300 transition-colors shadow-lg"
            >
              Ver catálogo completo →
            </Link>
            <a
              href="https://wa.me/573206876633"
              target="_blank"
              rel="noopener noreferrer"
              className="px-7 py-3.5 rounded-full bg-green-500 text-white font-semibold text-lg hover:bg-green-400 transition-colors shadow-lg"
            >
              💬 WhatsApp
            </a>
          </div>

          {/* Delivery badge */}
          <div className="mt-8 inline-flex items-center gap-2 bg-white/10 rounded-full px-5 py-2.5 text-sm">
            <Truck className="h-4 w-4" />
            Envío gratis en pedidos desde $30.000
          </div>
        </div>
      </section>
    </>
  );
}
