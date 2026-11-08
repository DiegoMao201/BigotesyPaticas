/** Producto como lo pinta la tienda del portal: une lo que trae /v1/products/catalog
 *  (con stock, marca y precio de antes) y lo que trae la búsqueda o el top 5. */
export interface ShopProduct {
  id: string;
  name: string;
  slug?: string;
  sku?: string | null;
  price: number;
  compare_at_price?: number | null;
  image_url: string | null;
  brand?: string | null;
  in_stock?: boolean;
  stock_qty?: number | null;
  rating_avg?: number | null;
  rating_count?: number | null;
  short_description?: string | null;
}

/** Normaliza cualquier forma de producto de la API a ShopProduct. */
export function toShop(p: Record<string, unknown>): ShopProduct {
  const brand = p.brand as { name?: string } | string | null | undefined;
  return {
    id: String(p.id),
    name: String(p.name ?? ''),
    slug: (p.slug as string) ?? undefined,
    sku: (p.sku as string) ?? null,
    price: Number(p.price ?? 0),
    compare_at_price: p.compare_at_price != null ? Number(p.compare_at_price) : null,
    image_url: ((p.image_url ?? p.primary_image_url) as string) ?? null,
    brand: typeof brand === 'string' ? brand : brand?.name ?? null,
    in_stock: p.in_stock as boolean | undefined,
    stock_qty: (p.stock_qty as number) ?? null,
    rating_avg: p.rating_avg != null ? Number(p.rating_avg) : null,
    rating_count: p.rating_count != null ? Number(p.rating_count) : null,
    short_description: (p.short_description as string) ?? null,
  };
}
