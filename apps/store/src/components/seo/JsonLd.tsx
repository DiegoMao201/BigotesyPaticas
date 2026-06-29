import { BUSINESS_INFO } from '@/lib/business-info';

// ─── Tipos ────────────────────────────────────────────────────────────────────

export interface FAQ {
  pregunta: string;
  respuesta: string;
}

export interface BreadcrumbItem {
  name: string;
  url: string;
}

interface ProductData {
  name: string;
  slug: string;
  sku?: string | null;
  brand?: { name: string } | null;
  category?: { name: string; slug: string } | null;
  price: string | number;
  in_stock: boolean;
  primary_image_url?: string | null;
  images?: string[];
  short_description?: string | null;
  enriched_content?: {
    descripcion?: string;
    descripcion_corta?: string;
    faqs?: FAQ[];
  } | null;
  rating_avg?: number | null;
  rating_count?: number;
  recent_reviews?: Array<{
    rating: number;
    title: string | null;
    comment: string | null;
    reviewer_name: string;
    created_at: string;
  }>;
}

interface ArticleData {
  title: string;
  slug: string;
  cover_image_url?: string | null;
  published_at?: string | null;
  updated_at?: string | null;
  meta_description?: string | null;
  excerpt?: string | null;
}

// ─── Helper interno ──────────────────────────────────────────────────────────

function JsonLd({ data }: { data: object }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

// ─── OrganizationSchema ───────────────────────────────────────────────────────
// Renderizar UNA VEZ en layout.tsx (root)

export function OrganizationSchema() {
  return (
    <JsonLd
      data={{
        '@context': 'https://schema.org',
        '@type': 'Organization',
        '@id': `${BUSINESS_INFO.url}/#organization`,
        name: BUSINESS_INFO.name,
        alternateName: BUSINESS_INFO.alternateName,
        legalName: BUSINESS_INFO.legalName,
        taxID: BUSINESS_INFO.legal.nit,
        url: BUSINESS_INFO.url,
        logo: {
          '@type': 'ImageObject',
          url: BUSINESS_INFO.logo,
          width: 512,
          height: 512,
        },
        image: BUSINESS_INFO.logo,
        description: BUSINESS_INFO.description,
        address: {
          '@type': 'PostalAddress',
          ...BUSINESS_INFO.address,
        },
        contactPoint: [
          {
            '@type': 'ContactPoint',
            telephone: BUSINESS_INFO.phone,
            contactType: 'customer service',
            email: BUSINESS_INFO.email,
            areaServed: [...BUSINESS_INFO.areaServed],
            availableLanguage: 'Spanish',
          },
        ],
        ...(BUSINESS_INFO.sameAs.length > 0 && { sameAs: [...BUSINESS_INFO.sameAs] }),
      }}
    />
  );
}

// ─── LocalBusinessSchema ──────────────────────────────────────────────────────
// Renderizar UNA VEZ en layout.tsx (root)

export function LocalBusinessSchema() {
  return (
    <JsonLd
      data={{
        '@context': 'https://schema.org',
        '@type': 'PetStore',
        '@id': `${BUSINESS_INFO.url}/#localbusiness`,
        name: BUSINESS_INFO.name,
        alternateName: [
          'Pet Shop Pereira',
          'Pet Shop Dosquebradas',
          'Petshop Pereira',
          'Petshop Dosquebradas',
          'Bigotes y Paticas Dosquebradas',
        ],
        keywords: 'pet shop Pereira, pet shop Dosquebradas, petshop Pereira, petshop Dosquebradas, domicilio pet shop, tienda mascotas Pereira, tienda mascotas Dosquebradas, concentrado perro Pereira, comida gato Dosquebradas, domicilio mascotas Risaralda',
        description: BUSINESS_INFO.description,
        image: [BUSINESS_INFO.logo],
        url: BUSINESS_INFO.url,
        telephone: BUSINESS_INFO.phone,
        email: BUSINESS_INFO.email,
        priceRange: BUSINESS_INFO.priceRange,
        currenciesAccepted: BUSINESS_INFO.currenciesAccepted,
        paymentAccepted: [...BUSINESS_INFO.paymentMethods].join(', '),
        address: {
          '@type': 'PostalAddress',
          ...BUSINESS_INFO.address,
        },
        geo: {
          '@type': 'GeoCoordinates',
          latitude: BUSINESS_INFO.geo.latitude,
          longitude: BUSINESS_INFO.geo.longitude,
        },
        hasMap: BUSINESS_INFO.mapsUrl,
        openingHoursSpecification: BUSINESS_INFO.openingHours.map((h) => ({
          '@type': 'OpeningHoursSpecification',
          dayOfWeek: [...h.days],
          opens: h.opens,
          closes: h.closes,
        })),
        areaServed: BUSINESS_INFO.areaServed.map((city) => ({
          '@type': 'City',
          name: city,
          containedInPlace: {
            '@type': 'AdministrativeArea',
            name: 'Risaralda',
          },
        })),
        amenityFeature: [
          BUSINESS_INFO.features.wheelchairAccessibleEntrance && {
            '@type': 'LocationFeatureSpecification',
            name: 'Wheelchair-accessible entrance',
            value: true,
          },
          BUSINESS_INFO.features.homeDelivery && {
            '@type': 'LocationFeatureSpecification',
            name: 'Home delivery',
            value: true,
          },
          BUSINESS_INFO.features.curbsidePickup && {
            '@type': 'LocationFeatureSpecification',
            name: 'Curbside pickup',
            value: true,
          },
          BUSINESS_INFO.features.inStorePickup && {
            '@type': 'LocationFeatureSpecification',
            name: 'In-store pickup',
            value: true,
          },
        ].filter(Boolean),
        aggregateRating: {
          '@type': 'AggregateRating',
          ratingValue: BUSINESS_INFO.rating.value,
          reviewCount: BUSINESS_INFO.rating.reviewCount,
          bestRating: BUSINESS_INFO.rating.bestRating,
        },
      }}
    />
  );
}

// ─── ProductSchema ────────────────────────────────────────────────────────────
// Renderizar en cada página de producto

export function ProductSchema({ product }: { product: ProductData }) {
  const enriched = product.enriched_content;
  const description =
    enriched?.descripcion ||
    enriched?.descripcion_corta ||
    product.short_description ||
    product.name;

  const imageUrls = [
    product.primary_image_url,
    ...(product.images ?? []),
  ].filter(Boolean) as string[];

  const price = Number(product.price);
  const priceValidUntil = new Date();
  priceValidUntil.setMonth(priceValidUntil.getMonth() + 6);

  const hasRating = (product.rating_count ?? 0) > 0 && product.rating_avg != null;

  const schema: Record<string, unknown> = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.name,
    ...(imageUrls.length > 0 && { image: imageUrls }),
    description,
    sku: product.sku ?? undefined,
    mpn: product.sku ?? undefined,
    brand: {
      '@type': 'Brand',
      name: product.brand?.name || 'Bigotes y Paticas',
    },
    ...(product.category?.name && { category: product.category.name }),
    ...(hasRating && {
      aggregateRating: {
        '@type': 'AggregateRating',
        ratingValue: product.rating_avg!.toFixed(1),
        reviewCount: product.rating_count,
        bestRating: '5',
        worstRating: '1',
      },
    }),
    ...(hasRating && product.recent_reviews && product.recent_reviews.length > 0 && {
      review: product.recent_reviews.slice(0, 5).map((r) => ({
        '@type': 'Review',
        reviewRating: {
          '@type': 'Rating',
          ratingValue: r.rating,
          bestRating: '5',
          worstRating: '1',
        },
        name: r.title || `Reseña de ${r.reviewer_name}`,
        reviewBody: r.comment || undefined,
        author: { '@type': 'Person', name: r.reviewer_name },
        datePublished: r.created_at.split('T')[0],
        publisher: { '@type': 'Organization', name: 'Bigotes y Paticas' },
      })),
    }),
    offers: {
      '@type': 'Offer',
      url: `${BUSINESS_INFO.url}/producto/${product.slug}`,
      priceCurrency: 'COP',
      price,
      priceValidUntil: priceValidUntil.toISOString().split('T')[0],
      availability: product.in_stock
        ? 'https://schema.org/InStock'
        : 'https://schema.org/OutOfStock',
      itemCondition: 'https://schema.org/NewCondition',
      seller: {
        '@type': 'Organization',
        '@id': `${BUSINESS_INFO.url}/#organization`,
      },
      shippingDetails: {
        '@type': 'OfferShippingDetails',
        shippingRate: {
          '@type': 'MonetaryAmount',
          value:
            price >= BUSINESS_INFO.shipping.freeShippingMinimum
              ? '0'
              : String(BUSINESS_INFO.shipping.standardShippingCost),
          currency: 'COP',
        },
        shippingDestination: BUSINESS_INFO.areaServed.map((city) => ({
          '@type': 'DefinedRegion',
          addressCountry: 'CO',
          addressRegion: 'Risaralda',
          addressLocality: city,
        })),
        deliveryTime: {
          '@type': 'ShippingDeliveryTime',
          handlingTime: {
            '@type': 'QuantitativeValue',
            minValue: BUSINESS_INFO.shipping.handlingDaysMin,
            maxValue: BUSINESS_INFO.shipping.handlingDaysMax,
            unitCode: 'DAY',
          },
          transitTime: {
            '@type': 'QuantitativeValue',
            minValue: BUSINESS_INFO.shipping.transitDaysMin,
            maxValue: BUSINESS_INFO.shipping.transitDaysMax,
            unitCode: 'DAY',
          },
        },
      },
      hasMerchantReturnPolicy: {
        '@type': 'MerchantReturnPolicy',
        applicableCountry: BUSINESS_INFO.returns.country,
        returnPolicyCategory:
          'https://schema.org/MerchantReturnFiniteReturnWindow',
        merchantReturnDays: BUSINESS_INFO.returns.window,
        returnMethod: `https://schema.org/${BUSINESS_INFO.returns.method}`,
        returnFees: `https://schema.org/${BUSINESS_INFO.returns.fees}`,
      },
    },
  };

  return <JsonLd data={schema} />;
}

// ─── BreadcrumbSchema ────────────────────────────────────────────────────────
// Renderizar en producto, categoría, blog, landing

export function BreadcrumbSchema({ items }: { items: BreadcrumbItem[] }) {
  return (
    <JsonLd
      data={{
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: items.map((item, idx) => ({
          '@type': 'ListItem',
          position: idx + 1,
          name: item.name,
          item: item.url,
        })),
      }}
    />
  );
}

// ─── FAQPageSchema ────────────────────────────────────────────────────────────
// Renderizar en producto si hay FAQs en enriched_content

export function FAQPageSchema({ faqs }: { faqs: FAQ[] }) {
  if (!faqs || faqs.length === 0) return null;
  return (
    <JsonLd
      data={{
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: faqs.map((f) => ({
          '@type': 'Question',
          name: f.pregunta,
          acceptedAnswer: { '@type': 'Answer', text: f.respuesta },
        })),
      }}
    />
  );
}

// ─── ArticleSchema ────────────────────────────────────────────────────────────
// Renderizar en posts del blog

export function ArticleSchema({ post }: { post: ArticleData }) {
  return (
    <JsonLd
      data={{
        '@context': 'https://schema.org',
        '@type': 'Article',
        headline: post.title,
        ...(post.cover_image_url && { image: [post.cover_image_url] }),
        ...(post.published_at && { datePublished: post.published_at }),
        ...(post.updated_at && { dateModified: post.updated_at }),
        author: {
          '@type': 'Organization',
          '@id': `${BUSINESS_INFO.url}/#organization`,
          name: BUSINESS_INFO.name,
        },
        publisher: {
          '@type': 'Organization',
          '@id': `${BUSINESS_INFO.url}/#organization`,
          name: BUSINESS_INFO.name,
          logo: {
            '@type': 'ImageObject',
            url: BUSINESS_INFO.logo,
          },
        },
        description: post.meta_description || post.excerpt || undefined,
        mainEntityOfPage: {
          '@type': 'WebPage',
          '@id': `${BUSINESS_INFO.url}/blog/${post.slug}`,
        },
      }}
    />
  );
}
