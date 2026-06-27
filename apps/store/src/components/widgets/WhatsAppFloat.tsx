'use client';

import { useEffect, useMemo, useState } from 'react';
import { usePathname } from 'next/navigation';
import { MessageCircle } from 'lucide-react';
import { useCart } from '@/lib/cart-store';
import { generateContextualMessage, getWhatsAppUrl } from '@/lib/whatsapp-messages';

export function WhatsAppFloat() {
  const cart = useCart();
  const pathname = usePathname();
  const [show, setShow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShow(true), 8000);
    return () => clearTimeout(timer);
  }, []);

  const itemCount = cart.count();

  const href = useMemo(() => {
    const cartItems = cart.items.map((i) => ({
      name: i.name,
      quantity: i.quantity,
      price: i.price,
    }));
    const message = generateContextualMessage(pathname, {
      items: cartItems,
      subtotal: () => cart.subtotal(),
    });
    return getWhatsAppUrl(message);
  }, [pathname, itemCount, cart]);

  function handleClick() {
    if (typeof window !== 'undefined' && 'gtag' in window) {
      (window as any).gtag('event', 'whatsapp_float_click', {
        page_path: pathname,
        cart_items_count: itemCount,
        cart_value: cart.subtotal(),
      });
    }
  }

  if (!show) return null;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      onClick={handleClick}
      className="fixed bottom-6 right-6 z-50 group"
      aria-label="Hablar por WhatsApp"
    >
      <div className="relative">
        <div className="absolute inset-0 rounded-full bg-green-500 opacity-30 animate-ping" />
        <div className="relative bg-green-500 hover:bg-green-600 text-white rounded-full shadow-2xl flex items-center gap-3 px-4 py-3 transition-all duration-200">
          <MessageCircle className="w-6 h-6 shrink-0" />
          {itemCount > 0 && (
            <span className="absolute -top-2 -right-2 bg-[#f5a641] text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center border-2 border-white">
              {itemCount}
            </span>
          )}
          <span className="hidden md:inline-block whitespace-nowrap font-semibold text-sm">
            {itemCount > 0 ? 'Pedir por WhatsApp' : 'Habla con nosotros'}
          </span>
        </div>
      </div>
    </a>
  );
}
