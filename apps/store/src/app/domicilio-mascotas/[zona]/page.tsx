import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { BreadcrumbSchema, FAQPageSchema } from '@/components/seo/JsonLd';
import { ZONAS, zonaPorSlug } from '@/data/zonas';

/**
 * Una página por zona de Pereira y Dosquebradas.
 *
 * Diego quiere salir "en cualquier búsqueda de animales en Pereira Dosquebradas".
 * La página de /pereira-dosquebradas-mascotas cubre las dos ciudades en bloque,
 * pero quien busca escribe el nombre de SU barrio, y esa consulta no tenía dónde
 * aterrizar. Estas 31 páginas le dan a cada comuna una entrada propia.
 *
 * El contenido de cada una es la lista real de sus barrios (724 en total, de Datos
 * Abiertos de Colombia; ver src/data/zonas.ts). No son páginas puerta: cada una
 * dice algo distinto y comprobable, no el mismo texto con el nombre cambiado.
 */

const BASE = 'https://bigotesypaticas.com';

export const revalidate = 86400;

export function generateStaticParams() {
  return ZONAS.map((z) => ({ zona: z.slug }));
}

export function generateMetadata({ params }: { params: { zona: string } }): Metadata {
  const z = zonaPorSlug(params.zona);
  if (!z) return {};
  const url = `${BASE}/domicilio-mascotas/${z.slug}`;
  const titulo = `Tienda de Mascotas con Domicilio en ${z.nombre}, ${z.ciudad}`;
  return {
    title: { absolute: `${titulo} | Bigotes y Paticas` },
    description:
      `Pet shop con domicilio en ${z.nombre} y los barrios de ${z.comuna}, ${z.ciudad}. ` +
      `Concentrado, snacks, accesorios y medicamentos veterinarios para perros y gatos. ` +
      `Envío gratis desde $30.000 y entrega el mismo día.`,
    keywords: [
      `tienda de mascotas ${z.nombre}`,
      `pet shop ${z.nombre}`,
      `petshop ${z.nombre} ${z.ciudad}`,
      `domicilio mascotas ${z.nombre}`,
      `concentrado perros ${z.nombre}`,
      `comida gatos ${z.nombre}`,
      `veterinaria ${z.nombre} ${z.ciudad}`,
      `tienda animales ${z.ciudad}`,
    ],
    alternates: { canonical: url },
    openGraph: { title: titulo, url, description: `Domicilio en ${z.nombre}, ${z.ciudad}. Más de 500 productos para perros y gatos.` },
  };
}

const CATEGORIAS = [
  { slug: 'perros', emoji: '🐕', label: 'Alimento y snacks para perros' },
  { slug: 'gatos', emoji: '🐈', label: 'Alimento y snacks para gatos' },
  { slug: 'accesorios', emoji: '🎀', label: 'Accesorios y juguetes' },
  { slug: 'snacks', emoji: '🦴', label: 'Premios y golosinas' },
];

export default function ZonaPage({ params }: { params: { zona: string } }) {
  const z = zonaPorSlug(params.zona);
  if (!z) notFound();

  const url = `${BASE}/domicilio-mascotas/${z.slug}`;
  const wa = `https://wa.me/573206876633?text=${encodeURIComponent(
    `Hola! Quiero pedir con domicilio en ${z.nombre}, ${z.ciudad}`,
  )}`;

  // Las otras zonas de la misma ciudad: enlaces internos reales entre páginas
  // hermanas, que es lo que hace que Google las recorra todas.
  const hermanas = ZONAS.filter((o) => o.ciudad === z.ciudad && o.slug !== z.slug);

  const faqs = [
    {
      pregunta: `¿Hacen domicilios en ${z.nombre}, ${z.ciudad}?`,
      respuesta:
        `Sí. Bigotes y Paticas lleva a domicilio en ${z.nombre} y en todos los barrios de ${z.comuna}. ` +
        `El envío es gratis en compras desde $30.000 y entregamos el mismo día siempre que sea posible.`,
    },
    {
      pregunta: `¿Dónde queda la tienda física?`,
      respuesta:
        'En Samara Plaza Mall, Cl. 15 #3A-07 Local 2, Dosquebradas, Risaralda. ' +
        'Atendemos de lunes a sábado de 10:00 a 19:00.',
    },
    {
      pregunta: `¿Qué puedo pedir para mi perro o mi gato?`,
      respuesta:
        'Concentrado de marcas como Royal Canin, Hills, Pro Plan, Taste of the Wild, Chunky y Agility Gold, ' +
        'además de snacks, arena, accesorios, juguetes y medicamentos veterinarios. Más de 500 productos en el catálogo.',
    },
  ];

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: BASE },
          { name: 'Pereira y Dosquebradas', url: `${BASE}/pereira-dosquebradas-mascotas` },
          { name: `${z.nombre}, ${z.ciudad}`, url },
        ]}
      />
      <FAQPageSchema faqs={faqs} />

      <div className="container-wide py-12">
        <div className="max-w-3xl mb-14">
          <p className="text-brand-600 font-semibold text-sm mb-2 uppercase tracking-wider">
            {z.ciudad} · {z.comuna} · Risaralda
          </p>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold leading-tight mb-5 text-[#0d4a45]">
            Tienda de mascotas con domicilio en {z.nombre}, {z.ciudad}
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed mb-4">
            <strong>Bigotes y Paticas</strong> lleva a domicilio hasta {z.nombre} todo lo que tu perro o tu
            gato necesita: concentrado premium, snacks, arena, accesorios, juguetes y medicamentos
            veterinarios. Somos una tienda física, no un catálogo: el local está en Samara Plaza Mall,
            sobre la calle 15 de Dosquebradas, y puedes venir a ver el producto antes de llevarlo.
          </p>
          <p className="text-lg text-muted-foreground leading-relaxed mb-8">
            Cubrimos los <strong>{z.barrios.length} barrios</strong> de {z.comuna} y entregamos{' '}
            <strong>el mismo día</strong> siempre que sea posible. Envío gratis desde $30.000.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/categorias/todos"
              className="px-6 py-3.5 rounded-full gradient-brand text-white font-semibold shadow-lg hover:opacity-90 transition-opacity"
            >
              Ver catálogo completo →
            </Link>
            <a
              href={wa}
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3.5 rounded-full bg-green-500 text-white font-semibold shadow-lg hover:bg-green-600 transition-colors"
            >
              Pedir por WhatsApp
            </a>
          </div>
        </div>

        <section className="mb-14">
          <h2 className="text-2xl font-display font-bold mb-5 text-[#0d4a45]">
            Qué puedes pedir en {z.nombre}
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {CATEGORIAS.map((c) => (
              <Link
                key={c.slug}
                href={`/categorias/${c.slug}`}
                className="rounded-2xl border border-border p-5 hover:shadow-md transition-shadow"
              >
                <span className="text-3xl block mb-2">{c.emoji}</span>
                <span className="font-semibold text-sm">{c.label}</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="mb-14">
          <h2 className="text-2xl font-display font-bold mb-3 text-[#0d4a45]">
            Barrios de {z.comuna} con domicilio
          </h2>
          <p className="text-muted-foreground mb-5">
            Estos son los {z.barrios.length} barrios de {z.comuna} en {z.ciudad}. Si el tuyo no aparece,
            escríbenos igual por WhatsApp: seguramente también llegamos.
          </p>
          <ul className="flex flex-wrap gap-2">
            {z.barrios.map((b) => (
              <li
                key={b}
                className="px-3 py-1.5 rounded-full bg-brand-50 text-brand-700 text-sm border border-brand-100"
              >
                {b}
              </li>
            ))}
          </ul>
        </section>

        <section className="mb-14">
          <h2 className="text-2xl font-display font-bold mb-5 text-[#0d4a45]">Preguntas frecuentes</h2>
          <div className="space-y-5 max-w-3xl">
            {faqs.map((f) => (
              <div key={f.pregunta}>
                <h3 className="font-semibold mb-1.5">{f.pregunta}</h3>
                <p className="text-muted-foreground leading-relaxed">{f.respuesta}</p>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-2xl font-display font-bold mb-5 text-[#0d4a45]">
            Otras zonas de {z.ciudad} con domicilio
          </h2>
          <ul className="flex flex-wrap gap-2">
            {hermanas.map((o) => (
              <li key={o.slug}>
                <Link
                  href={`/domicilio-mascotas/${o.slug}`}
                  className="px-3.5 py-2 rounded-full border border-border text-sm hover:bg-brand-50 hover:border-brand-200 transition-colors inline-block"
                >
                  {o.nombre}
                </Link>
              </li>
            ))}
          </ul>
          <p className="mt-6">
            <Link href="/domicilio-mascotas" className="text-brand-600 font-semibold hover:underline">
              Ver todas las zonas de Pereira y Dosquebradas →
            </Link>
          </p>
        </section>
      </div>
    </>
  );
}
