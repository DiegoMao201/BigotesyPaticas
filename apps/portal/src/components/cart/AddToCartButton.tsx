'use client';

import { useState } from 'react';
import { toast } from 'sonner';
import { ShoppingCart } from 'lucide-react';
import { usePortalCart } from '@/lib/cart-store';

interface Props {
  product: {
    id: string;
    sku: string;
    name: string;
    price: number;
    image_url?: string | null;
  };
  quantity?: number;
  className?: string;
}

export function AddToCartButton({ product, quantity = 1, className }: Props) {
  const [bounce, setBounce] = useState(false);
  const addItem = usePortalCart((s) => s.addItem);

  function handleAdd() {
    addItem({
      product_id: product.id,
      sku: product.sku ?? '',
      name: product.name,
      image_url: product.image_url ?? null,
      unit_price: product.price,
      quantity,
    });
    toast.success('Producto agregado al carrito 🛒');
    setBounce(true);
    setTimeout(() => setBounce(false), 600);
  }

  return (
    <button
      onClick={handleAdd}
      className={`flex items-center justify-center gap-2 py-3 px-5 rounded-2xl font-bold text-white transition-all ${bounce ? 'scale-95' : 'scale-100'} ${className ?? 'bg-teal-600 hover:bg-teal-700 w-full'}`}
    >
      <ShoppingCart className={`h-5 w-5 ${bounce ? 'animate-bounce' : ''}`} />
      Agregar al carrito
    </button>
  );
}
