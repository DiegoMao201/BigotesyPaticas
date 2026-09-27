'use client';

// Tarjeta de producto ÚNICA para catálogo y búsqueda (27-sep-2026). En celular: 2
// columnas, nombre de 2 líneas legible, precio grande y botón "Agregar" sin entrar a
// la ficha; en escritorio conserva el tamaño compacto de antes.
import Link from 'next/link';
import Image from 'next/image';
import { Heart, MessageCircle, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { formatCurrency } from '@/lib/utils';
import type { Product } from '@/lib/api';
import { getOutOfStockWhatsAppUrl } from '@/lib/whatsapp-messages';
import { useCart } from '@/lib/cart-store';
import { trackAddToCart } from '@/lib/analytics';

export function ProductTile({ p }: { p: Product }) {
  const add = useCart((st) => st.add);
  const discount =
    p.compare_at_price && Number(p.compare_at_price) > Number(p.price)
      ? Math.round((1 - Number(p.price) / Number(p.compare_at_price)) * 100)
      : null;

  return (
    <Link
      href={`/producto/${p.slug}`}
      className="group block relative bg-white rounded-2xl overflow-hidden
                 border border-gray-100 hover:border-[#187f77]/40
                 hover:shadow-lg hover:shadow-black/5
                 transition-all duration-200"
    >
      {/* Imagen */}
      <div className="relative aspect-square bg-[#F8F9FA] overflow-hidden">
        {p.primary_image_url ? (
          <Image
            src={p.primary_image_url}
            alt={p.name}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 768px) 33vw, (max-width: 1024px) 25vw, (max-width: 1280px) 20vw, 16vw"
            className={`object-contain p-3
                       group-hover:scale-105 transition-transform duration-300
                       ${!p.in_stock ? 'grayscale opacity-70' : ''}`}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-4xl opacity-25">
            🐾
          </div>
        )}

        {/* Badge stock */}
        <div className="absolute top-2 left-2">
          {p.in_stock ? (
            <span className="bg-[#187f77] text-white text-[10px] md:text-[9px] font-bold
                             px-2 py-0.5 rounded-full uppercase tracking-wide">
              Disponible
            </span>
          ) : (
            <span className="bg-amber-100 text-amber-700 text-[10px] md:text-[9px] font-bold
                             px-2 py-0.5 rounded-full uppercase tracking-wide border border-amber-200">
              Agotado
            </span>
          )}
        </div>

        {/* Badge descuento */}
        {discount && (
          <div className="absolute top-1.5 right-1.5">
            <span className="bg-[#f5a641] text-white text-[9px] font-bold
                             px-1.5 py-0.5 rounded-full">
              -{discount}%
            </span>
          </div>
        )}

        {/* Favorito (hover desktop / siempre móvil) */}
        <button
          onClick={(e) => e.preventDefault()}
          aria-label="Guardar"
          className="absolute bottom-2 right-2 w-9 h-9 md:w-7 md:h-7 rounded-full bg-white
                     shadow-md flex items-center justify-center
                     opacity-100 sm:opacity-0 sm:group-hover:opacity-100
                     transition-opacity duration-150"
        >
          <Heart className="w-4 h-4 md:w-3.5 md:h-3.5 text-gray-500" />
        </button>
      </div>

      {/* Info compacta */}
      <div className="p-3 md:p-2.5 space-y-1 md:space-y-0.5">
        {(p.category?.name || p.brand?.name) && (
          <p className="text-[10px] md:text-[9px] text-gray-400 uppercase tracking-wide truncate">
            {p.category?.name}
            {p.brand?.name ? ` · ${p.brand.name}` : ''}
          </p>
        )}
        <h3 className="text-sm md:text-xs font-semibold text-[#0d4a45] line-clamp-2
                       leading-snug md:leading-tight min-h-[2.5rem] md:min-h-[2rem]">
          {p.name}
        </h3>
        <div className="flex items-baseline gap-1 pt-0.5">
          {discount && p.compare_at_price && (
            <span className="text-xs md:text-[10px] text-gray-400 line-through">
              {formatCurrency(p.compare_at_price)}
            </span>
          )}
          <span
            className={`text-lg md:text-sm font-bold ${
              p.in_stock ? 'text-[#187f77]' : 'text-gray-400'
            }`}
          >
            {formatCurrency(p.price)}
          </span>
        </div>
        {p.in_stock ? (
          // Comprar sin salir del catálogo (en celular es lo que más se usa)
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              add({ productId: p.id, slug: p.slug, name: p.name, price: Number(p.price) || 0, image: p.primary_image_url ?? null });
              trackAddToCart({ id: p.id, name: p.name, price: Number(p.price) || 0, quantity: 1 });
              toast.success('Agregado al carrito', { description: p.name });
            }}
            className="mt-1.5 flex items-center justify-center gap-1.5 w-full h-10 md:h-8 rounded-xl
                       bg-[#187f77] hover:bg-[#0d4a45] active:scale-[0.98] text-white text-sm md:text-xs font-bold
                       transition-all"
          >
            <Plus className="w-4 h-4 md:w-3.5 md:h-3.5" /> Agregar
          </button>
        ) : (
          // Antes era un <a> dentro del <Link> de la tarjeta: enlace dentro de enlace
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              window.open(getOutOfStockWhatsAppUrl({
                name: p.name,
                brand: p.brand ? { name: p.brand.name } : null,
                price: p.price,
                slug: p.slug,
              }), '_blank', 'noopener,noreferrer');
            }}
            className="mt-1.5 flex items-center justify-center gap-1.5 w-full h-10 md:h-8 rounded-xl
                       bg-green-500 hover:bg-green-600 text-white text-xs md:text-[10px] font-bold
                       transition-colors"
          >
            <MessageCircle className="w-4 h-4 md:w-3 md:h-3" />
            Lo consigo por WhatsApp
          </button>
        )}
      </div>
    </Link>  );
}
