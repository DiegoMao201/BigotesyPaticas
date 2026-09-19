import type { Metadata } from 'next';
import Link from 'next/link';
import { BreadcrumbSchema, ItemListSchema } from '@/components/seo/JsonLd';
import { ZONAS } from '@/data/zonas';

/** El índice de las 31 zonas: desde aquí Google entra a todas. */

const BASE = 'https://bigotesypaticas.com';

export const metadata: Metadata = {
  title: { absolute: 'Domicilio de Mascotas por Zonas de Pereira y Dosquebradas' },
  description:
    'Bigotes y Paticas lleva concentrado, snacks, accesorios y medicamentos veterinarios a domicilio en las 19 comunas de Pereira y las 12 de Dosquebradas. Envío gratis desde $30.000.',
  alternates: { canonical: `${BASE}/domicilio-mascotas` },
};

export default function ZonasPage() {
  const pereira = ZONAS.filter((z) => z.ciudad === 'Pereira');
  const dosquebradas = ZONAS.filter((z) => z.ciudad === 'Dosquebradas');
  const barrios = ZONAS.reduce((n, z) => n + z.barrios.length, 0);

  return (
    <>
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: BASE },
          { name: 'Zonas con domicilio', url: `${BASE}/domicilio-mascotas` },
        ]}
      />
      <ItemListSchema
        name="Zonas con domicilio en Pereira y Dosquebradas"
        url={`${BASE}/domicilio-mascotas`}
        items={ZONAS.map((z) => ({
          name: `${z.nombre}, ${z.ciudad}`,
          url: `${BASE}/domicilio-mascotas/${z.slug}`,
        }))}
      />

      <div className="container-wide py-12">
        <div className="max-w-3xl mb-14">
          <p className="text-brand-600 font-semibold text-sm mb-2 uppercase tracking-wider">
            Risaralda · {ZONAS.length} zonas · {barrios} barrios
          </p>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold leading-tight mb-5 text-[#0d4a45]">
            Domicilio de mascotas por zonas de Pereira y Dosquebradas
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed">
            Llevamos concentrado, snacks, arena, accesorios y medicamentos veterinarios a las{' '}
            <strong>19 comunas de Pereira</strong> y a las <strong>12 de Dosquebradas</strong>. Busca tu
            zona y mira los barrios que cubre. Envío gratis desde $30.000 y entrega el mismo día siempre
            que sea posible.
          </p>
        </div>

        {[
          { titulo: 'Pereira', lista: pereira },
          { titulo: 'Dosquebradas', lista: dosquebradas },
        ].map(({ titulo, lista }) => (
          <section key={titulo} className="mb-14">
            <h2 className="text-2xl font-display font-bold mb-5 text-[#0d4a45]">
              {titulo} · {lista.length} zonas
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {lista.map((z) => (
                <Link
                  key={z.slug}
                  href={`/domicilio-mascotas/${z.slug}`}
                  className="rounded-2xl border border-border p-5 hover:shadow-md hover:border-brand-200 transition-all"
                >
                  <span className="font-semibold block mb-1">{z.nombre}</span>
                  <span className="text-sm text-muted-foreground">
                    {z.comuna} · {z.barrios.length} barrios
                  </span>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </>
  );
}
