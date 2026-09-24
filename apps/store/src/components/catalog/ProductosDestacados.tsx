import Image from 'next/image';
import Link from 'next/link';
import { formatCurrency } from '@/lib/utils';
import type { Product } from '@/lib/api';

/**
 * Rejilla de productos REALES con foto y precio.
 *
 * POR QUE EXISTE (24-sep-2026). La landing /pereira-dosquebradas-mascotas es la
 * que más gente atrae de todo el sitio (2.575 impresiones en Search Console) y
 * es donde MENOS se quedan: 58 segundos, contra 157 en /adopcion y 185 en la
 * portada. Al mirarla, la razón salta: no muestra ni un producto ni un precio.
 * Quien busca "tienda de mascotas pereira" quiere ver qué vendes y a cómo, y le
 * dábamos siete bloques de texto.
 *
 * /adopcion, que retiene el triple y genera más contactos por WhatsApp que
 * ninguna otra página, hace justo lo contrario: enseña cosas reales con foto.
 * Esto copia eso, que es evidencia de la propia casa y no una teoría.
 */
export function ProductosDestacados({
  productos, titulo, bajada, cuantos = 8,
}: { productos: Product[]; titulo: string; bajada?: string; cuantos?: number }) {
  const items = productos.filter((p) => p.primary_image_url).slice(0, cuantos);
  if (!items.length) return null;

  return (
    <section className="mb-16">
      <div className="flex items-end justify-between mb-6 gap-4">
        <div>
          <h2 className="text-2xl font-display font-bold text-[#0d4a45]">{titulo}</h2>
          {bajada && <p className="text-muted-foreground text-sm mt-1">{bajada}</p>}
        </div>
        <Link
          href="/categorias/todos"
          className="text-sm font-semibold text-brand-600 hover:text-brand-500 whitespace-nowrap"
        >
          Ver los 500+ →
        </Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
        {items.map((p) => (
          <Link
            key={p.id}
            href={`/producto/${p.slug}`}
            className="group rounded-2xl overflow-hidden border border-border bg-card transition-all hover:shadow-warm hover:-translate-y-1 duration-300"
          >
            <div className="aspect-square bg-white relative p-3">
              <Image
                src={p.primary_image_url as string}
                alt={p.name}
                fill
                sizes="(max-width: 768px) 50vw, 25vw"
                className="object-contain p-2 group-hover:scale-105 transition-transform duration-300"
              />
            </div>
            <div className="p-3 border-t border-border">
              <p className="text-xs text-muted-foreground line-clamp-1">{p.brand?.name ?? ' '}</p>
              <p className="font-semibold text-sm leading-snug line-clamp-2 min-h-[2.5rem]">{p.name}</p>
              <p className="font-display font-extrabold text-[#0d4a45] mt-1">
                {formatCurrency(p.price)}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
