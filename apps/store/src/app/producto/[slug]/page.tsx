import { notFound } from 'next/navigation';
import { storeApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { AddToCart } from './add-to-cart';
import { Truck, ShieldCheck, RefreshCw } from 'lucide-react';

export const dynamic = 'force-dynamic';

export default async function ProductPage({ params }: { params: { slug: string } }) {
  const product = await storeApi.bySlug(params.slug);
  if (!product) notFound();

  return (
    <div className="container-wide py-12 grid lg:grid-cols-2 gap-12">
      <div className="aspect-square bg-secondary rounded-3xl overflow-hidden">
        {product.primary_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={product.primary_image_url} alt={product.name} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[12rem]">🐾</div>
        )}
      </div>

      <div className="space-y-6">
        <div>
          <p className="text-xs text-muted-foreground font-mono uppercase tracking-wider">
            SKU {product.sku}
          </p>
          <h1 className="text-4xl md:text-5xl font-display font-bold mt-2">{product.name}</h1>
          {product.short_description && (
            <p className="text-lg text-muted-foreground mt-3">{product.short_description}</p>
          )}
        </div>

        <div className="flex items-baseline gap-3">
          <span className="text-4xl font-display font-bold text-gradient">
            {formatCurrency(product.price)}
          </span>
          {product.compare_at_price && (
            <span className="text-lg text-muted-foreground line-through">
              {formatCurrency(product.compare_at_price)}
            </span>
          )}
        </div>

        <AddToCart
          product={{
            productId: product.id,
            slug: product.slug,
            name: product.name,
            price: parseFloat(product.price),
            image: product.primary_image_url,
          }}
        />

        {product.description && (
          <div className="prose prose-sm max-w-none">
            <h3 className="font-display font-semibold text-sm uppercase tracking-wider">Descripción</h3>
            <p className="text-muted-foreground leading-relaxed">{product.description}</p>
          </div>
        )}

        <div className="grid grid-cols-3 gap-4 pt-6 border-t border-border">
          <div className="flex flex-col items-center text-center text-xs text-muted-foreground">
            <Truck className="h-5 w-5 text-brand mb-1" /> Envío 24-72h
          </div>
          <div className="flex flex-col items-center text-center text-xs text-muted-foreground">
            <ShieldCheck className="h-5 w-5 text-brand mb-1" /> Pago seguro
          </div>
          <div className="flex flex-col items-center text-center text-xs text-muted-foreground">
            <RefreshCw className="h-5 w-5 text-brand mb-1" /> Devolución 30d
          </div>
        </div>
      </div>
    </div>
  );
}
