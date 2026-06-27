export function trackEvent(name: string, params: Record<string, unknown> = {}) {
  if (typeof window === 'undefined' || typeof window.gtag !== 'function') return;
  window.gtag('event', name, params);
}

export function trackViewItem(product: {
  id: string;
  name: string;
  category?: string;
  brand?: string;
  price: number;
}) {
  trackEvent('view_item', {
    currency: 'COP',
    value: product.price,
    items: [{
      item_id: product.id,
      item_name: product.name,
      item_category: product.category,
      item_brand: product.brand,
      price: product.price,
      quantity: 1,
    }],
  });
}

export function trackAddToCart(product: {
  id: string;
  name: string;
  price: number;
  quantity?: number;
}) {
  trackEvent('add_to_cart', {
    currency: 'COP',
    value: product.price * (product.quantity ?? 1),
    items: [{
      item_id: product.id,
      item_name: product.name,
      price: product.price,
      quantity: product.quantity ?? 1,
    }],
  });
}

export function trackSearch(query: string) {
  trackEvent('search', { search_term: query });
}
