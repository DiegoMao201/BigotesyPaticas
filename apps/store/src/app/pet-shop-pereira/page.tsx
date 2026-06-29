import type { Metadata } from 'next';
import Link from 'next/link';
import { LocalBusinessSchema, BreadcrumbSchema } from '@/components/seo/JsonLd';

export const metadata: Metadata = {
  title: 'Pet Shop Pereira — Bigotes y Paticas | Domicilio a domicilio 24h',
  description:
    'El mejor pet shop de Pereira con domicilio a domicilio. Concentrados, accesorios, medicamentos veterinarios para perros y gatos. Envío gratis desde $30.000. Petshop con domicilio en Dosquebradas y Risaralda.',
  keywords: [
    'pet shop Pereira',
    'petshop Pereira',
    'pet shop domicilio Pereira',
    'domicilio pet shop Pereira',
    'pet shop cerca Pereira',
    'pet shop Dosquebradas',
    'petshop Dosquebradas',
    'tienda mascotas Pereira',
    'pet shop Risaralda',
    'tienda animales Pereira',
    'donde comprar comida para perros Pereira',
    'donde comprar comida para gatos Pereira',
    'pet shop con domicilio',
    'Hills Science Diet Pereira',
    'Royal Canin Pereira',
    'Pro Plan Pereira',
    'concentrado perros Pereira',
    'comida gatos Pereira',
    'medicamentos veterinarios Pereira',
    'accesorios mascotas Pereira',
  ],
  alternates: { canonical: 'https://bigotesypaticas.com/pet-shop-pereira' },
  openGraph: {
    title: 'Pet Shop Pereira con Domicilio — Bigotes y Paticas',
    description:
      'Pet shop con domicilio en Pereira y Dosquebradas. Más de 900 productos para perros y gatos. Envío gratis desde $30.000.',
    url: 'https://bigotesypaticas.com/pet-shop-pereira',
  },
};

const MARCAS = [
  "Hill's Science Diet", "Royal Canin", "Pro Plan", "Purina",
  "Acana", "Orijen", "Taste of the Wild", "Diamond",
  "Eukanuba", "Pedigree", "Whiskas", "Fancy Feast",
  "Bravecto", "Nexgard", "Frontline", "Drontal",
];

const PRODUCTOS = [
  { emoji: '🥩', label: 'Concentrado para perros', sub: 'Todas las razas y tamaños', slug: 'perros' },
  { emoji: '🐱', label: 'Concentrado para gatos', sub: 'Gatitos, adultos y seniors', slug: 'gatos' },
  { emoji: '🦴', label: 'Snacks y premios', sub: 'Golosinas saludables', slug: 'snacks' },
  { emoji: '🎀', label: 'Accesorios', sub: 'Correas, collares, camas, juguetes', slug: 'accesorios' },
  { emoji: '💊', label: 'Medicamentos', sub: 'Antiparasitarios y vitaminas', slug: 'todos' },
  { emoji: '🛁', label: 'Aseo y peluquería', sub: 'Shampús y cepillos', slug: 'todos' },
];

const FAQS = [
  {
    q: '¿Bigotes y Paticas es el pet shop con domicilio más rápido de Pereira?',
    a: 'Sí. Somos el pet shop de Pereira con entrega en 24 a 72 horas a cualquier barrio. Puedes hacer tu pedido en nuestra tienda online o por WhatsApp y lo recibes en la puerta de tu casa.',
  },
  {
    q: '¿Qué marcas de concentrado venden en el pet shop?',
    a: 'En nuestro pet shop tenemos Hill\'s Science Diet, Royal Canin, Pro Plan, Acana, Orijen, Taste of the Wild, Purina, Pedigree, Whiskas, Fancy Feast y muchas más. Más de 900 productos disponibles para domicilio en Pereira y Dosquebradas.',
  },
  {
    q: '¿El pet shop tiene domicilio gratis en Pereira?',
    a: 'Sí, el domicilio es gratis en compras desde $30.000. Cubrimos toda la zona urbana de Pereira, desde el Centro hasta Cerritos, Cuba, Pinares y todos los barrios.',
  },
  {
    q: '¿El pet shop también cubre Dosquebradas?',
    a: 'Por supuesto. Nuestra sede física está en Dosquebradas (Mall Zamara Plaza) y hacemos domicilio en toda la zona urbana de Dosquebradas, incluyendo La Capilla, Frailes, Los Naranjos, Badillo y más.',
  },
  {
    q: '¿Puedo comprar medicamentos veterinarios en el pet shop sin receta?',
    a: 'Tenemos productos antiparasitarios externos (Bravecto, Nexgard, Frontline) y vitaminas disponibles sin receta. Para medicamentos con prescripción te asesoramos por WhatsApp.',
  },
  {
    q: '¿El pet shop tiene productos para gatos en Pereira?',
    a: 'Sí. Tenemos una completa línea para gatos: concentrado, snacks, arenas sanitarias, accesorios, juguetes y más. Todo disponible con domicilio en Pereira y Dosquebradas.',
  },
];

export default function PetShopPereiraPage() {
  return (
    <>
      <LocalBusinessSchema />
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Pet Shop Pereira', url: 'https://bigotesypaticas.com/pet-shop-pereira' },
        ]}
      />

      <div className="container-wide py-12">

        {/* Hero */}
        <div className="max-w-3xl mb-16">
          <p className="text-brand-600 font-semibold text-sm mb-2 uppercase tracking-wider">
            Pet Shop · Pereira · Dosquebradas · Risaralda
          </p>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold leading-tight mb-5 text-[#0d4a45]">
            Pet Shop en Pereira con domicilio a tu puerta
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed mb-4">
            <strong>Bigotes y Paticas</strong> es el pet shop de Pereira y Dosquebradas con domicilio en 24-72 horas.
            Somos tu petshop online con más de <strong>900 productos</strong> para perros y gatos:
            concentrado, snacks, accesorios, medicamentos veterinarios y más.
          </p>
          <p className="text-lg text-muted-foreground leading-relaxed mb-8">
            Envío gratis en compras desde <strong>$30.000</strong> a cualquier barrio de Pereira y Dosquebradas.
            Tu pet shop con domicilio en Risaralda.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/categorias/todos"
              className="px-6 py-3.5 rounded-full gradient-brand text-white font-semibold shadow-lg hover:opacity-90 transition-opacity"
            >
              Ver catálogo del pet shop →
            </Link>
            <a
              href="https://wa.me/573206876633?text=Hola!%20Quiero%20pedir%20en%20el%20pet%20shop%20con%20domicilio%20en%20Pereira"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3.5 rounded-full bg-green-500 text-white font-semibold shadow-lg hover:bg-green-600 transition-colors"
            >
              💬 Pedir por WhatsApp
            </a>
          </div>
        </div>

        {/* Productos */}
        <section className="mb-16">
          <h2 className="text-2xl font-display font-bold mb-2 text-[#0d4a45]">
            Productos del pet shop disponibles con domicilio
          </h2>
          <p className="text-muted-foreground mb-6">
            Todo lo que tu mascota necesita, entregado en Pereira y Dosquebradas:
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {PRODUCTOS.map((p) => (
              <Link
                key={p.label}
                href={`/categorias/${p.slug}`}
                className="group block rounded-2xl border border-border bg-card p-5 hover:border-teal-300 hover:bg-teal-50 transition-all"
              >
                <div className="text-3xl mb-3">{p.emoji}</div>
                <p className="font-semibold text-sm group-hover:text-teal-700">{p.label}</p>
                <p className="text-xs text-muted-foreground mt-1">{p.sub}</p>
              </Link>
            ))}
          </div>
        </section>

        {/* Por qué elegirnos */}
        <section className="mb-16 rounded-3xl bg-gradient-to-br from-teal-600 to-teal-900 text-white p-10">
          <h2 className="text-2xl font-display font-bold mb-8">
            ¿Por qué somos el mejor pet shop de Pereira?
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: '🚚',
                title: 'Domicilio rápido en Pereira',
                desc: 'Entrega en 24-72h a cualquier barrio de Pereira y Dosquebradas. Domicilio gratis desde $30.000. Tu petshop a domicilio.',
              },
              {
                icon: '🏪',
                title: '+900 productos en el pet shop',
                desc: 'Hill\'s, Royal Canin, Pro Plan, Acana, Orijen, Bravecto, Nexgard y muchas marcas más. El pet shop con más variedad de Risaralda.',
              },
              {
                icon: '⭐',
                title: 'Calidad premium garantizada',
                desc: 'Todos los productos de nuestro pet shop son originales y verificados. Atención personalizada por WhatsApp para ayudarte a elegir.',
              },
            ].map((b) => (
              <div key={b.title}>
                <div className="text-4xl mb-3">{b.icon}</div>
                <h3 className="font-bold text-lg mb-2">{b.title}</h3>
                <p className="text-teal-100 text-sm leading-relaxed">{b.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Marcas */}
        <section className="mb-16">
          <h2 className="text-2xl font-display font-bold mb-3 text-[#0d4a45]">
            Marcas en el pet shop con domicilio en Pereira
          </h2>
          <p className="text-muted-foreground mb-6">
            En nuestro pet shop de Pereira encontrarás las marcas más reconocidas del mercado:
          </p>
          <div className="flex flex-wrap gap-3">
            {MARCAS.map((m) => (
              <span
                key={m}
                className="px-4 py-2 rounded-full text-sm border border-border bg-card font-medium"
              >
                {m}
              </span>
            ))}
          </div>
        </section>

        {/* FAQ */}
        <section className="mb-16">
          <h2 className="text-2xl font-display font-bold mb-8 text-[#0d4a45]">
            Preguntas frecuentes sobre el pet shop
          </h2>
          <div className="space-y-5">
            {FAQS.map((item) => (
              <div key={item.q} className="rounded-2xl border border-border bg-card p-6">
                <h3 className="font-display font-bold text-lg mb-2 text-[#0d4a45]">{item.q}</h3>
                <p className="text-muted-foreground leading-relaxed">{item.a}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="text-center rounded-3xl bg-[#0d4a45] text-white p-12">
          <div className="text-5xl mb-4">🐾</div>
          <h2 className="text-3xl font-display font-bold mb-3">
            Tu pet shop con domicilio en Pereira y Dosquebradas
          </h2>
          <p className="text-teal-200 mb-8 text-lg max-w-lg mx-auto">
            Más de 900 productos para tu mascota. Pide hoy y recibe mañana.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href="/categorias/todos"
              className="px-8 py-4 rounded-full bg-[#f5a641] text-[#0d4a45] font-bold text-lg hover:bg-amber-300 transition-colors"
            >
              Ver catálogo →
            </Link>
            <a
              href="https://wa.me/573206876633"
              target="_blank"
              rel="noopener noreferrer"
              className="px-8 py-4 rounded-full bg-green-500 text-white font-bold text-lg hover:bg-green-400 transition-colors"
            >
              💬 WhatsApp
            </a>
          </div>
        </section>

      </div>
    </>
  );
}
