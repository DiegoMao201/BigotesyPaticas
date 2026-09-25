import type { Metadata } from 'next';
import Link from 'next/link';
import { BreadcrumbSchema } from '@/components/seo/JsonLd';
import { ProductosDestacados } from '@/components/catalog/ProductosDestacados';
import { ZonaModalButton } from '@/components/maps/ZonaModalButton';
import { storeApi } from '@/lib/api';
import { fichaGoogle } from '@/lib/ficha-google';

export const metadata: Metadata = {
  // 19-sep-2026: Pereira primero (216 impresiones vs 131 de Dosquebradas en
  // Search Console) y "domicilio el mismo día" en el título, que es lo que
  // diferencia de las tiendas que salen al lado. Descripción ≤155 caracteres.
  title: { absolute: 'Tienda de Mascotas Pereira y Dosquebradas · Domicilio Hoy' },
  description:
    'Tienda de mascotas en Samara Plaza Mall, Dosquebradas, con domicilio en Pereira. Concentrado, accesorios y medicamentos. 5,0 ★ en Google. Envío gratis.',
  keywords: [
    'pet shop Pereira', 'petshop Pereira', 'pet shop Dosquebradas',
    'domicilio pet shop Pereira', 'pet shop domicilio Risaralda',
    'tienda mascotas Pereira', 'tienda mascotas Dosquebradas',
    'domicilio mascotas Pereira', 'concentrado perros Pereira',
    'comida gatos Dosquebradas', 'veterinaria Pereira',
    'accesorios mascotas Risaralda', 'medicamentos veterinarios Pereira',
    'Hills Pereira', 'Royal Canin Dosquebradas', 'Pro Plan Pereira',
    'tienda animales Pereira', 'comida mascota domicilio Pereira',
  ],
  alternates: { canonical: 'https://bigotesypaticas.com/pereira-dosquebradas-mascotas' },
  openGraph: {
    title: 'Tienda de mascotas en Pereira y Dosquebradas | Bigotes y Paticas',
    description:
      'Entrega el mismo día, lo más rápido posible, en toda la zona urbana. Concentrados premium, accesorios y medicamentos para perros y gatos.',
    url: 'https://bigotesypaticas.com/pereira-dosquebradas-mascotas',
  },
};

const PEREIRA_BARRIOS = [
  'Centro', 'Pinares', 'Cuba', 'Belmonte', 'Álamos', 'El Jardín', 'Galería',
  'Olímpica', 'La Villa', 'Av. 30 de Agosto', 'Cerritos', 'Circunvalar',
  'El Poblado', 'San Fernando', 'Boston', 'Parque Industrial',
];

const DOSQUEBRADAS_BARRIOS = [
  'La Capilla', 'Frailes', 'Los Naranjos', 'Badillo', 'La Esneda',
  'Santa Teresita', 'El Corinto', 'Campestre', 'Las Vegas', 'El Japón',
  'La Pradera', 'San Diego', 'Valher', 'Otún', 'Villa del Campo',
];

const CATEGORIAS = [
  { slug: 'perros', emoji: '🐕', label: 'Alimentos y snacks para perros' },
  { slug: 'gatos', emoji: '🐈', label: 'Alimentos y snacks para gatos' },
  { slug: 'accesorios', emoji: '🎀', label: 'Accesorios y juguetes' },
  { slug: 'snacks', emoji: '🦴', label: 'Premios y golosinas' },
];

// SEGURO CONTRA EL FALLO SILENCIOSO. La rejilla se arma en el build. Si el API
// no responde justo en ese momento, la página saldría SIN productos y nadie se
// enteraría hasta mirar el HTML a mano (pasó en la primera prueba). Con esto se
// regenera cada hora: un build malo se cura solo en 60 minutos en vez de durar
// hasta el siguiente despliegue.
export const revalidate = 3600;

export default async function PereiraPage() {
  // Si el catálogo no responde, la página sigue saliendo sin la rejilla:
  // una landing que carga a medias es mejor que una que revienta.
  const [destacados, ficha] = await Promise.all([
    storeApi.featured().catch(() => []),
    fichaGoogle(),
  ]);

  return (
    <>
      {/* La ficha del negocio ya la emite layout.tsx en TODAS las páginas. Tenerla
          dos veces en la misma página deja dos PetStore idénticos y Google no sabe
          cuál es la entidad buena; con una sola y su @id, la consolida. */}
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Pereira y Dosquebradas', url: 'https://bigotesypaticas.com/pereira-dosquebradas-mascotas' },
        ]}
      />

      <div className="container-wide py-12">
        {/* Hero */}
        <div className="max-w-3xl mb-16">
          <p className="text-brand-600 font-semibold text-sm mb-2 uppercase tracking-wider">
            Pereira · Dosquebradas · Risaralda
          </p>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold leading-tight mb-5 text-[#0d4a45]">
            Tienda de mascotas y pet shop con domicilio en Pereira y Dosquebradas
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed mb-4">
            <strong>Bigotes y Paticas</strong> es la tienda de mascotas y pet shop de Dosquebradas, en Samara
            Plaza Mall sobre la calle 15, y llevamos a domicilio hasta Pereira todo lo que tu perro o gato
            necesita: concentrado premium, accesorios, juguetes, arena y medicamentos veterinarios.
          </p>
          <p className="text-lg text-muted-foreground leading-relaxed mb-5">
            Domicilio <strong>el mismo día</strong> en toda la zona urbana. Más de 500 productos.
          </p>
          {/* La prueba social va ARRIBA, junto al botón, no escondida abajo: es lo
              que decide si confían antes de escribir. 5,0 con 28 reseñas es real,
              está verificado en la ficha de Google. */}
          {ficha && (
            <p className="text-sm font-semibold text-[#0d4a45] mb-6">
              ★★★★★ {ficha.nota.toLocaleString('es-CO', { minimumFractionDigits: 1 })} ·{' '}
              {ficha.resenas} reseñas en Google
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <Link
              href="/categorias/todos"
              className="brillo px-6 py-3.5 rounded-full gradient-brand text-white font-semibold shadow-lg hover:opacity-90 transition-opacity"
            >
              Ver catálogo completo →
            </Link>
            <a
              href="https://wa.me/573206876633?text=%C2%A1Hola%2C%20Bigotes%20y%20Paticas%21%20%F0%9F%90%BE%0A%0ALos%20encontr%C3%A9%20en%20Google%20y%20quiero%20pedir%20con%20domicilio.%0A%0A%C2%BFMe%20confirman%20si%20llegan%20a%20mi%20zona%20y%20cu%C3%A1nto%20se%20demoran%3F%0A%0AMi%20barrio%20es%3A%20"
              target="_blank"
              rel="noopener noreferrer"
              className="brillo brillo-2 px-6 py-3.5 rounded-full bg-green-500 text-white font-semibold shadow-lg hover:bg-green-600 transition-colors"
            >
              💬 Pedir por WhatsApp
            </a>
            {/* Diego (24-sep-2026): "al lado de ese botón de WhatsApp y catálogo
                colócale un botón que diga llegamos a tu zona, míralo y pum,
                oprimen y sale una ventanita con el mapa". El comprobador ya
                existía y solo vivía en la ficha de producto y en /contacto. */}
            <ZonaModalButton variante="pildora" />
          </div>
        </div>

        {/* LO PRIMERO DESPUES DEL HERO: MERCANCIA DE VERDAD.
            Antes aquí venían categorías, beneficios, barrios, marcas y preguntas
            —siete bloques de texto— y ni un solo producto. La gente llegaba
            buscando "tienda de mascotas pereira" y se iba a los 58 segundos. */}
        <ProductosDestacados
          productos={destacados}
          titulo="Lo que más piden en Pereira y Dosquebradas"
          bajada="Con domicilio el mismo día · envío gratis desde $30.000"
        />

        {/* Categorías */}
        <section className="mb-16">
          <h2 className="text-2xl font-display font-bold mb-6 text-[#0d4a45]">
            Productos disponibles con envío a Pereira y Dosquebradas
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {CATEGORIAS.map((c) => (
              <Link
                key={c.slug}
                href={`/categorias/${c.slug}`}
                className="group block rounded-2xl border border-border bg-card p-5 hover:border-teal-300 hover:bg-teal-50 transition-all"
              >
                <div className="text-4xl mb-3">{c.emoji}</div>
                <p className="font-semibold text-sm group-hover:text-teal-700">{c.label}</p>
              </Link>
            ))}
          </div>
        </section>

        {/* Beneficios */}
        <section className="mb-16 rounded-3xl bg-gradient-to-br from-teal-600 to-teal-900 text-white p-10">
          <h2 className="text-2xl font-display font-bold mb-8">
            ¿Por qué elegir Bigotes y Paticas en Pereira?
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: '🚚',
                title: 'Envío rápido a domicilio',
                desc: 'Recibe tu pedido el mismo día en cualquier barrio de Pereira y Dosquebradas. Envío gratis desde $30.000.',
              },
              {
                icon: '⭐',
                title: 'Marcas premium verificadas',
                desc: 'Hill\'s Science Diet, Royal Canin, Pro Plan, Bravecto y más de 500 productos seleccionados por veterinarios.',
              },
              {
                icon: '🐾',
                title: 'Portal de fidelización',
                desc: 'Crea tu cuenta gratis, acumula puntos en cada compra, lleva el carnet digital de salud de tu mascota y recibe recordatorios de vacunas.',
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

        {/* Cobertura */}
        <section className="mb-16">
          <h2 className="text-2xl font-display font-bold mb-3 text-[#0d4a45]">
            Pet shop con domicilio en Pereira: zonas que cubrimos
          </h2>
          <p className="text-muted-foreground mb-6">
            Cubrimos toda la zona urbana de Pereira. Algunos de los barrios que atendemos:
          </p>
          <div className="flex flex-wrap gap-2 mb-8">
            {PEREIRA_BARRIOS.map((b) => (
              <span
                key={b}
                className="px-3 py-1.5 rounded-full text-sm bg-orange-50 border border-orange-100 text-orange-700 font-medium"
              >
                {b}
              </span>
            ))}
            <span className="px-3 py-1.5 rounded-full text-sm bg-orange-50 border border-orange-100 text-orange-500 italic">
              y más barrios...
            </span>
          </div>

          <h2 className="text-2xl font-display font-bold mb-3 text-[#0d4a45]">
            Tienda de mascotas en Dosquebradas: cobertura de domicilio
          </h2>
          <p className="text-muted-foreground mb-6">
            Nuestra sede está en Dosquebradas. Entregamos en toda la zona urbana:
          </p>
          <div className="flex flex-wrap gap-2">
            {DOSQUEBRADAS_BARRIOS.map((b) => (
              <span
                key={b}
                className="px-3 py-1.5 rounded-full text-sm bg-teal-50 border border-teal-100 text-teal-700 font-medium"
              >
                {b}
              </span>
            ))}
            <span className="px-3 py-1.5 rounded-full text-sm bg-teal-50 border border-teal-100 text-teal-500 italic">
              y más barrios...
            </span>
          </div>
        </section>

        {/* Marcas */}
        <section className="mb-16">
          <h2 className="text-2xl font-display font-bold mb-6 text-[#0d4a45]">
            Marcas disponibles con envío en Pereira y Dosquebradas
          </h2>
          <div className="flex flex-wrap gap-3">
            {[
              "Hill's Science Diet", "Royal Canin", "Pro Plan", "Bravecto",
              "Nexgard", "Frontline", "Drontal", "Advocate", "Acana",
              "Orijen", "Taste of the Wild", "Diamond", "Eukanuba", "Pedigree",
              "Whiskas", "Fancy Feast", "Purina", "Nutram",
            ].map((m) => (
              <span
                key={m}
                className="px-4 py-2 rounded-full text-sm border border-border bg-card font-medium"
              >
                {m}
              </span>
            ))}
          </div>
        </section>

        {/* FAQ SEO */}
        <section className="mb-16">
          <h2 className="text-2xl font-display font-bold mb-8 text-[#0d4a45]">
            Preguntas frecuentes
          </h2>
          <div className="space-y-5">
            {[
              {
                q: '¿Cuánto demora el envío a domicilio en Pereira?',
                a: 'Entregamos el mismo día en toda la zona urbana de Pereira. Escríbenos por WhatsApp y coordinamos tu pedido para enviarlo de inmediato.',
              },
              {
                q: '¿Entregan en todos los barrios de Dosquebradas?',
                a: 'Sí, cubrimos toda la zona urbana de Dosquebradas. Nuestra sede está en Dosquebradas y tenemos conocimiento del municipio para garantizar entregas rápidas.',
              },
              {
                q: '¿Cuánto cuesta el domicilio de mascotas en Pereira?',
                a: 'El envío es gratis en compras desde $30.000. Para pedidos menores se cobra un costo de envío que varía según la zona. Consulta por WhatsApp para conocer el costo exacto.',
              },
              {
                q: '¿Tienen Royal Canin en Pereira con domicilio?',
                a: 'Sí, contamos con toda la línea Royal Canin para perros y gatos disponible para domicilio en Pereira y Dosquebradas. Ingresa a nuestro catálogo para ver disponibilidad y precios.',
              },
              {
                q: '¿Cómo hago un pedido de mascotas a domicilio en Dosquebradas?',
                a: 'Puedes hacer tu pedido directamente en nuestra tienda online, seleccionando los productos y completando tu información de entrega. También puedes escribirnos por WhatsApp al +57 320 687 6633.',
              },
              {
                q: '¿Bigotes y Paticas es un pet shop?',
                a: 'Sí, somos el pet shop de Pereira y Dosquebradas con más variedad y el mejor servicio de domicilio de Risaralda. Nuestro petshop tiene más de 500 productos para perros, gatos y otras mascotas, con envío gratis desde $30.000.',
              },
              {
                q: '¿Qué es un pet shop y qué venden?',
                a: 'Un pet shop es una tienda especializada en productos para mascotas. En nuestro pet shop de Pereira encontrarás concentrado para perros y gatos, snacks, accesorios, correas, collares, camas, juguetes, medicamentos antiparasitarios y productos de aseo para mascotas.',
              },
            ].map((item) => (
              <div key={item.q} className="rounded-2xl border border-border bg-card p-6">
                <h3 className="font-display font-bold text-lg mb-2 text-[#0d4a45]">{item.q}</h3>
                <p className="text-muted-foreground leading-relaxed">{item.a}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA Final */}
        <section className="text-center rounded-3xl bg-[#0d4a45] text-white p-12">
          <div className="text-5xl mb-4">🐾</div>
          <h2 className="text-3xl font-display font-bold mb-3">
            ¿Listo para pedir con domicilio en Pereira o Dosquebradas?
          </h2>
          <p className="text-teal-200 mb-8 text-lg max-w-lg mx-auto">
            Explora nuestro catálogo de más de 500 productos y recíbelos en la puerta de tu casa.
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
