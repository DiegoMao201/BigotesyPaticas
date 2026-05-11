import { storeApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

export default async function CategoryPage({ params }: { params: { slug: string } }) {
  const data = await storeApi.list({ page_size: 24 });
  const slug = decodeURIComponent(params.slug);

  return (
    <div className="container-wide py-12">
      <h1 className="text-4xl md:text-5xl font-display font-bold capitalize">{slug}</h1>
      <p className="text-muted-foreground mt-2">{data.total} productos disponibles</p>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 mt-8">
        {data.items.map((p) => (
          <Link
            key={p.id}
            href={`/producto/${p.slug}`}
            className="group rounded-2xl overflow-hidden border border-border bg-card transition-all hover:shadow-elegant hover:-translate-y-1"
          >
            <div className="aspect-square bg-secondary relative">
              {p.primary_image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={p.primary_image_url} alt={p.name} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-6xl">🐾</div>
              )}
              <div className={`absolute top-2 left-2 text-xs font-medium px-2 py-0.5 rounded-full ${
                p.in_stock
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-gray-100 text-gray-500'
              }`}>
                {p.in_stock ? 'Disponible' : 'No disponible'}
              </div>
            </div>
            <div className="p-4">
              <h3 className="font-medium text-sm line-clamp-2 group-hover:text-brand">{p.name}</h3>
              <div className="font-bold mt-2">{formatCurrency(p.price)}</div>
            </div>
          </Link>
        ))}
      </div>

      {data.items.length === 0 && (
        <div className="text-center py-24 text-muted-foreground">
          <div className="text-6xl mb-4">🐾</div>
          <p>Pronto añadiremos productos a esta categoría.</p>
        </div>
      )}
    </div>
  );
}
