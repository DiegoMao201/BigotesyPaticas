'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { MeResponse } from './api';

interface AuthState {
  customer: MeResponse | null;
  isLoading: boolean;
  setCustomer: (c: MeResponse | null) => void;
  setLoading: (v: boolean) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      customer: null,
      isLoading: false,
      setCustomer: (customer) => set({ customer }),
      setLoading: (isLoading) => set({ isLoading }),
      clear: () => set({ customer: null }),
    }),
    {
      name: 'bp_portal_session',
      partialize: (s) => ({ customer: s.customer }),
    }
  )
);
