const WA_NUMBER = '573206876633';

export interface CartItemLike {
  name: string;
  quantity: number;
  price: number;
}

export function generateContextualMessage(
  pathname: string,
  cart: { items: CartItemLike[]; subtotal: () => number },
): string {
  if (cart.items.length > 0) {
    const total = cart.subtotal();
    const envio = total >= 30000 ? 0 : 8000;
    const lines = cart.items
      .map(
        (i) =>
          `• ${i.quantity}× ${i.name} — $${(i.price * i.quantity).toLocaleString('es-CO')}`,
      )
      .join('\n');

    return `¡Hola! Quiero hacer este pedido 🐾\n\n🛒 *Mi pedido:*\n${lines}\n\nSubtotal: $${total.toLocaleString('es-CO')}\n${envio === 0 ? '🎉 Envío GRATIS' : `Envío estándar: $${envio.toLocaleString('es-CO')}`}\n*Total: $${(total + envio).toLocaleString('es-CO')}*\n\n¿Me confirman disponibilidad y método de pago?`;
  }

  const productMatch = pathname.match(/^\/producto\/(.+)/);
  if (productMatch) {
    return `¡Hola! Estoy viendo este producto en su sitio:\n🔗 https://bigotesypaticas.com${pathname}\n\n¿Está disponible para entrega en Pereira/Dosquebradas?`;
  }

  const categoryMatch = pathname.match(/^\/categorias\/(.+)/);
  if (categoryMatch) {
    const cat = decodeURIComponent(categoryMatch[1]).replace(/-/g, ' ');
    return `¡Hola! Estoy buscando productos de ${cat} en su sitio. ¿Me orientan?`;
  }

  if (pathname.startsWith('/landing/')) {
    return '¡Hola! Llegué a su sitio buscando productos para mascotas en Pereira/Dosquebradas. ¿Pueden ayudarme?';
  }

  if (pathname.startsWith('/blog/')) {
    return '¡Hola! Estaba leyendo su blog y tengo una consulta sobre productos para mi mascota.';
  }

  return '¡Hola Bigotes y Paticas! Estoy en su sitio y tengo una consulta 🐾';
}

export function getOutOfStockWhatsAppUrl(product: {
  name: string;
  brand?: { name: string } | null;
  price: number | string;
  slug: string;
}): string {
  const price = Number(product.price).toLocaleString('es-CO');
  const brandLine = product.brand ? `🏷️ ${product.brand.name}\n` : '';
  const message = `¡Hola Bigotes y Paticas! 🐾\n\nEstoy en su sitio web y me interesa este producto que aparece agotado:\n\n📦 *${product.name}*\n${brandLine}💰 $${price}\n🔗 https://bigotesypaticas.com/producto/${product.slug}\n\n¿Pueden conseguirlo? ¿Cuánto tardarían?\n\nGracias`;

  return `https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(message)}`;
}

export function getWhatsAppUrl(message: string): string {
  return `https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(message)}`;
}
