import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { storeApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { AddToCart } from './add-to-cart';
import { ProductTabs } from './ProductTabs';
import { StickyCTAMobile } from './StickyCTAMobile';
import { ProductSchema, BreadcrumbSchema, FAQPageSchema } from '@/components/seo/JsonLd';
import { ProductFAQ } from '@/components/seo/ProductFAQ';
import { Truck, ShieldCheck, RefreshCw, ChevronRight, MessageCircle } from 'lucide-react';

export const dynamic = 'force-dynamic';

interface Props { params: { slug: string } }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const product = await storeApi.bySlug(params.slug);
  if (!product) return { title: 'Producto no encontrado | Bigotes y Paticas' };

  const seo = product.enriched_content?.seo;
  const enrichedDesc = product.enriched_content?.descripcion_corta;
  const priceStr = Number(product.price).toLocaleString('es-CO');

  return {
    title: seo?.meta_title || `${product.name} — $${priceStr} | Bigotes y Paticas`,
    description:
      seo?.meta_description ||
      enrichedDesc ||
      `Compra ${product.name} en Pereira y Dosquebradas. ${product.in_stock ? 'Disponible' : 'Próximamente'}. Envío 24-72h.`,
    keywords: seo?.keywords || [
      product.name,
      product.brand?.name || '',
      `${product.name} Pereira`,
      `${product.name} Dosquebradas`,
      product.category?.name || '',
    ].filter(Boolean),
    alternates: { canonical: `https://bigotesypaticas.com/producto/${product.slug}` },
    openGraph: {
      type: 'website',
      title: seo?.meta_title || product.name,
      description: seo?.meta_description || enrichedDesc || `Compra ${product.name} en Pereira`,
      url: `https://bigotesypaticas.com/producto/${product.slug}`,
      images: product.primary_image_url
        ? [{ url: product.primary_image_url, width: 800, height: 800, alt: product.name }]
        : [{ url: `/api/og?product=${encodeURIComponent(product.name)}&price=${product.price}`, width: 1200, height: 630 }],
    },
  };
}

const WA_NUMBER = process.env.NEXT_PUBLIC_WHATSAPP ?? '573206876633';

export default async function ProductPage({ params }: Props) {
  const product = await storeApi.bySlug(params.slug);
  if (!product) notFound();

  const related = await storeApi.related(product.id, 4);

  const discount =
    product.compare_at_price && Number(product.compare_at_price) > Number(product.price)
      ? Math.round((1 - Number(product.price) / Number(product.compare_at_price)) * 100)
      : null;

  const allImages = [
    product.primary_image_url,
    ...(product.images ?? []),
  ].filter(Boolean) as string[];

  const waMsg = encodeURIComponent(
    `Hola! Me interesa el producto: ${product.name} (SKU: ${product.sku}). ¿Está disponible?`
  );

  return (
    <>
      <ProductSchema
        name={product.name}
        description={product.enriched_content?.descripcion || product.short_description || undefined}
        imageUrl={product.primary_image_url || undefined}
        sku={product.sku}
        brand={product.brand?.name}
        price={product.price}
        inStock={product.in_stock}
        slug={product.slug}
      />
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          ...(product.category
            ? [{ name: product.category.name, url: `https://bigotesypaticas.com/categorias/${product.category.slug}` }]
            : []),
          { name: product.name, url: `https://bigotesypaticas.com/producto/${product.slug}` },
        ]}
      />
      {product.enriched_content?.faqs && product.enriched_content.faqs.length > 0 && (
        <FAQPageSchema faqs={product.enriched_content.faqs} />
      )}

      {/* Breadcrumbs */}
      <div className="container-wide py-4">
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground flex-wrap">
          <Link href="/" className="hover:text-brand-600 transition-colors">Inicio</Link>
          <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />
          {product.category && (
            <>
              <Link
                href={`/categorias/${product.category.slug}`}
                className="hover:text-brand-600 transition-colors capitalize"
              >
                {product.category.name}
              </Link>
              <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />
            </>
          )}
          <span className="text-foreground font-medium line-clamp-1">{product.name}</span>
        </div>
      </div>

      {/* Main content */}
      <div className="container-wide pb-12">
        <div className="grid lg:grid-cols-2 gap-10 xl:gap-16">

          {/* ── Imagen izquierda ── */}
          <div className="space-y-3">
            <div className="relative aspect-square rounded-3xl overflow-hidden bg-white border border-border shadow-sm">
              {allImages[0] ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={allImages[0]}
                  alt={product.name}
                  className="w-full h-full object-contain p-6"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-[9rem] bg-gradient-to-br from-orange-50 to-amber-50">
                  🐾
                </div>
              )}

              {/* Badges */}
              {discount && (
                <div className="absolute top-4 left-4 bg-brand-600 text-white text-sm font-bold px-3.5 py-1.5 rounded-2xl shadow-md">
                  -{discount}%
                </div>
              )}
              {!product.in_stock && (
                <div className="absolute inset-0 bg-white/70 backdrop-blur-[2px] flex items-center justify-center rounded-3xl">
                  <span className="text-red-600 font-bold text-xl bg-white rounded-2xl px-6 py-3 shadow-lg border border-red-100">
                    Agotado
                  </span>
                </div>
              )}
            </div>

            {/* Thumbnails */}
            {allImages.length > 1 && (
              <div className="grid grid-cols-4 gap-2.5">
                {allImages.slice(1, 5).map((img, i) => (
                  <div
                    key={i}
                    className="aspect-square rounded-2xl overflow-hidden border border-border bg-white"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={img}
                      alt={`${product.name} ${i + 2}`}
                      className="w-full h-full object-contain p-2"
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── Panel de compra derecha ── */}
          <div className="space-y-5 lg:pt-2">
            {/* Category pill */}
            {product.category && (
              <Link
                href={`/categorias/${product.category.slug}`}
                className="inline-block text-xs font-bold uppercase tracking-widest text-brand-600 bg-brand-50 px-3.5 py-1.5 rounded-full border border-brand-100 hover:bg-brand-100 transition-colors"
              >
                {product.category.name}
              </Link>
            )}

            {/* Nombre */}
            <h1 className="text-3xl md:text-4xl font-display font-extrabold leading-tight">
              {product.name}
            </h1>

            {/* SKU */}
            <p className="text-xs text-muted-foreground font-mono">SKU: {product.sku}</p>

            {/* Precio */}
            <div className="flex items-baseline gap-3 flex-wrap">
              <span className="text-4xl font-extrabold text-brand-600">
                {formatCurrency(product.price)}
              </span>
              {discount && product.compare_at_price && (
                <>
                  <span className="text-xl text-muted-foreground line-through">
                    {formatCurrency(product.compare_at_price)}
                  </span>
                  <span className="text-sm font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">
                    Ahorra {discount}%
                  </span>
                </>
              )}
            </div>

            {/* Stock */}
            <div className="flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                  product.in_stock ? 'bg-emerald-500 animate-pulse' : 'bg-red-400'
                }`}
              />
              <span
                className={`text-sm font-semibold ${
                  product.in_stock ? 'text-emerald-700' : 'text-red-600'
                }`}
              >
                {product.in_stock
                  ? `Disponible · ${product.stock_qty} unidades`
                  : 'Agotado'}
              </span>
            </div>

            {/* Short description */}
            {product.short_description && (
              <p className="text-muted-foreground leading-relaxed">{product.short_description}</p>
            )}

            {/* Add to cart */}
            {product.in_stock ? (
              <AddToCart
                product={{
                  productId: product.id,
                  slug: product.slug,
                  name: product.name,
                  price: parseFloat(product.price),
                  image: product.primary_image_url,
                }}
              />
            ) : (
              <div className="rounded-2xl border border-red-100 bg-red-50 p-4">
                <p className="text-sm font-semibold text-red-700">Este producto está agotado</p>
                <p className="text-xs text-red-500 mt-1">
                  Consulta disponibilidad por WhatsApp o prueba otro producto similar.
                </p>
              </div>
            )}

            {/* WhatsApp */}
            <a
              href={`https://wa.me/${WA_NUMBER}?text=${waMsg}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2.5 w-full py-3 rounded-2xl border-2 border-emerald-500 text-emerald-700 font-semibold hover:bg-emerald-50 transition-colors text-sm"
            >
              <MessageCircle className="h-4 w-4" />
              Consultar disponibilidad por WhatsApp
            </a>

            {/* Beneficios */}
            <div className="grid grid-cols-3 gap-3 pt-5 border-t border-border">
              <div className="flex flex-col items-center text-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-100 flex items-center justify-center">
                  <Truck className="h-5 w-5 text-teal-600" />
                </div>
                <span className="text-xs text-muted-foreground leading-tight">Envío 24-72h</span>
              </div>
              <div className="flex flex-col items-center text-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-100 flex items-center justify-center">
                  <ShieldCheck className="h-5 w-5 text-teal-600" />
                </div>
                <span className="text-xs text-muted-foreground leading-tight">Compra segura</span>
              </div>
              <div className="flex flex-col items-center text-center gap-2">
                <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-100 flex items-center justify-center">
                  <RefreshCw className="h-5 w-5 text-teal-600" />
                </div>
                <span className="text-xs text-muted-foreground leading-tight">Calidad garantizada</span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Tabs ── */}
        <div className="mt-14 border-t border-border pt-2">
          <ProductTabs product={product} />
        </div>

        {/* ── FAQs ── */}
        {product.enriched_content?.faqs && product.enriched_content.faqs.length > 0 && (
          <div className="mt-10 max-w-2xl">
            <ProductFAQ faqs={product.enriched_content.faqs} />
          </div>
        )}

        {/* ── Productos relacionados ── */}
        {related.length > 0 && (
          <div className="mt-16">
            <div className="mb-8">
              <p className="text-brand-600 font-semibold text-sm mb-1">Puede que también te guste</p>
              <h2 className="text-2xl md:text-3xl font-display font-extrabold">Productos relacionados</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
              {related.map((p) => {
                const relDiscount =
                  p.compare_at_price && Number(p.compare_at_price) > Number(p.price)
                    ? Math.round((1 - Number(p.price) / Number(p.compare_at_price)) * 100)
                    : null;
                return (
                  <Link
                    key={p.id}
                    href={`/producto/${p.slug}`}
                    className="group rounded-3xl overflow-hidden border border-border bg-card transition-all hover:shadow-warm hover:-translate-y-1 duration-300"
                  >
                    <div className="aspect-square bg-white flex items-center justify-center relative p-3">
                      {p.primary_image_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={p.primary_image_url}
                          alt={p.name}
                          className="w-full h-full object-contain drop-shadow-sm group-hover:scale-105 transition-transform duration-300"
                        />
                      ) : (
                        <div className="text-5xl group-hover:scale-110 transition-transform duration-300">🐾</div>
                      )}
                      {relDiscount && (
                        <div className="absolute top-2 right-2 text-xs font-bold px-2 py-0.5 rounded-full bg-brand-600 text-white">
                          -{relDiscount}%
                        </div>
                      )}
                    </div>
                    <div className="p-4">
                      <h3 className="font-semibold text-sm line-clamp-2 group-hover:text-brand-600 transition-colors">
                        {p.name}
                      </h3>
                      <div className="flex items-baseline gap-2 mt-2">
                        <span className="font-extrabold text-brand-600 text-sm">
                          {formatCurrency(p.price)}
                        </span>
                        {relDiscount && p.compare_at_price && (
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
          </div>
        )}
      </div>

      {/* Mobile sticky CTA — se muestra cuando el botón principal ya no es visible */}
      <StickyCTAMobile
        product={{
          productId: product.id,
          slug: product.slug,
          name: product.name,
          price: parseFloat(product.price),
          image: product.primary_image_url,
        }}
        inStock={product.in_stock}
      />
    </>
  );
}
