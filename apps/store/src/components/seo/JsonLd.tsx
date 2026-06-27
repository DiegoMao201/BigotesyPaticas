const CDN_LOGO =
  'https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/branding/logo-512.png';

export interface ProductSchemaProps {
  name: string;
  description?: string;
  imageUrl?: string;
  sku?: string;
  brand?: string;
  price: string | number;
  inStock: boolean;
  slug: string;
}

export interface BreadcrumbItem {
  name: string;
  url: string;
}

export interface FAQ {
  pregunta: string;
  respuesta: string;
}

export interface ArticleSchemaProps {
  title: string;
  description?: string;
  imageUrl?: string;
  publishedAt?: string;
  updatedAt?: string;
  author?: string;
  url: string;
}

function JsonLd({ data }: { data: object }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

export function OrganizationSchema() {
  return (
    <JsonLd
      data={{
        '@context': 'https://schema.org',
        '@type': 'Organization',
        name: 'Bigotes y Paticas',
        url: 'https://bigotesypaticas.com',
        logo: CDN_LOGO,
        description:
          'Tienda premium de productos para mascotas en Pereira y Dosquebradas, Risaralda, Colombia',
        address: {
          '@type': 'PostalAddress',
          addressLocality: 'Dosquebradas',
          addressRegion: 'Risaralda',
          postalCode: '661001',
          addressCountry: 'CO',
        },
        contactPoint: {
          '@type': 'ContactPoint',
          telephone: '+573206876633',
          contactType: 'customer service',
          email: 'bigotesypaticasdosquebradas@gmail.com',
          areaServed: 'CO',
          availableLanguage: 'Spanish',
        },
        sameAs: [
          'https://www.facebook.com/bigotesypaticas',
          'https://www.instagram.com/bigotesypaticas',
        ],
      }}
    />
  );
}

export function LocalBusinessSchema() {
  return (
    <JsonLd
      data={{
        '@context': 'https://schema.org',
        '@type': 'PetStore',
        name: 'Bigotes y Paticas',
        image: CDN_LOGO,
        '@id': 'https://bigotesypaticas.com',
        url: 'https://bigotesypaticas.com',
        telephone: '+573206876633',
        email: 'bigotesypaticasdosquebradas@gmail.com',
        priceRange: '$$',
        address: {
          '@type': 'PostalAddress',
          addressLocality: 'Dosquebradas',
          addressRegion: 'Risaralda',
          postalCode: '661001',
          addressCountry: 'CO',
        },
        geo: {
          '@type': 'GeoCoordinates',
          latitude: 4.8333,
          longitude: -75.6833,
        },
        openingHoursSpecification: [
          {
            '@type': 'OpeningHoursSpecification',
            dayOfWeek: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
            opens: '09:00',
            closes: '19:00',
          },
        ],
        areaServed: [
          { '@type': 'City', name: 'Pereira' },
          { '@type': 'City', name: 'Dosquebradas' },
        ],
        hasMap: 'https://maps.google.com/?q=Dosquebradas,Risaralda,Colombia',
      }}
    />
  );
}

export function ProductSchema({
  name, description, imageUrl, sku, brand, price, inStock, slug,
}: ProductSchemaProps) {
  return (
    <JsonLd
      data={{
        '@context': 'https://schema.org',
        '@type': 'Product',
        name,
        ...(imageUrl && { image: [imageUrl] }),
        ...(description && { description }),
        ...(sku && { sku }),
        brand: { '@type': 'Brand', name: brand || 'Genérico' },
        offers: {
          '@type': 'Offer',
          url: `https://bigotesypaticas.com/producto/${slug}`,
          priceCurrency: 'COP',
          price: Number(price),
          availability: inStock
            ? 'https://schema.org/InStock'
            : 'https://schema.org/OutOfStock',
          seller: { '@type': 'Organization', name: 'Bigotes y Paticas' },
          areaServed: ['Pereira', 'Dosquebradas'],
        },
      }}
    />
  );
}

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

export function ArticleSchema({
  title, description, imageUrl, publishedAt, updatedAt, author, url,
}: ArticleSchemaProps) {
  return (
    <JsonLd
      data={{
        '@context': 'https://schema.org',
        '@type': 'Article',
        headline: title,
        ...(description && { description }),
        ...(imageUrl && { image: imageUrl }),
        ...(publishedAt && { datePublished: publishedAt }),
        ...(updatedAt && { dateModified: updatedAt }),
        author: {
          '@type': 'Organization',
          name: author || 'Equipo Bigotes y Paticas',
        },
        publisher: {
          '@type': 'Organization',
          name: 'Bigotes y Paticas',
          logo: { '@type': 'ImageObject', url: CDN_LOGO },
        },
        mainEntityOfPage: { '@type': 'WebPage', '@id': url },
      }}
    />
  );
}
