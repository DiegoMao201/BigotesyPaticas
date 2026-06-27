'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface CartItem {
  product_id: string;
  sku: string;
  name: string;
  image_url: string | null;
  unit_price: number;
  quantity: number;
  notes?: string;
}

interface CartStore {
  items: CartItem[];
  addItem: (product: CartItem) => void;
  removeItem: (product_id: string) => void;
  updateQuantity: (product_id: string, qty: number) => void;
  updateNotes: (product_id: string, notes: string) => void;
  clear: () => void;
  subtotal: () => number;
  pointsToEarn: () => number;
  isFreeShipping: () => boolean;
  itemCount: () => number;
}

export const usePortalCart = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],
      addItem: (product) =>
        set((state) => {
          const existing = state.items.find((i) => i.product_id === product.product_id);
          if (existing) {
            return {
              items: state.items.map((i) =>
                i.product_id === product.product_id
                  ? { ...i, quantity: i.quantity + product.quantity }
                  : i,
              ),
            };
          }
          return { items: [...state.items, product] };
        }),
      removeItem: (product_id) =>
        set((state) => ({ items: state.items.filter((i) => i.product_id !== product_id) })),
      updateQuantity: (product_id, qty) =>
        set((state) => ({
          items:
            qty <= 0
              ? state.items.filter((i) => i.product_id !== product_id)
              : state.items.map((i) =>
                  i.product_id === product_id ? { ...i, quantity: qty } : i,
                ),
        })),
      updateNotes: (product_id, notes) =>
        set((state) => ({
          items: state.items.map((i) =>
            i.product_id === product_id ? { ...i, notes } : i,
          ),
        })),
      clear: () => set({ items: [] }),
      subtotal: () => get().items.reduce((sum, i) => sum + i.unit_price * i.quantity, 0),
      pointsToEarn: () => Math.floor(get().subtotal() / 1000),
      isFreeShipping: () => get().subtotal() >= 30000,
      itemCount: () => get().items.reduce((sum, i) => sum + i.quantity, 0),
    }),
    { name: 'bp-portal-cart' },
  ),
);
