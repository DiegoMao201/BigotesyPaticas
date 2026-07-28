'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { PartnerUserInfo } from './api';

interface AuthState {
  partnerUser: PartnerUserInfo | null;
  token: string | null;
  refreshToken: string | null;
  hasHydrated: boolean;
  setSession: (partnerUser: PartnerUserInfo, token: string, refreshToken: string) => void;
  updatePartner: (partial: Partial<PartnerUserInfo['partner']>) => void;
  clear: () => void;
}

// `hasHydrated` evita un falso "no hay sesión" → redirect a /login en cada
// carga completa de página: zustand-persist rehidrata desde localStorage
// DESPUÉS del primer render en Next.js (para que coincida con el HTML del
// server, que no tiene localStorage), así que `token` es null por un
// instante aunque sí exista una sesión guardada. Sin este flag, cualquier
// guard que redirija apenas `!token` dispara antes de que la rehidratación
// termine.
export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      partnerUser: null,
      token: null,
      refreshToken: null,
      hasHydrated: false,
      setSession: (partnerUser, token, refreshToken) => set({ partnerUser, token, refreshToken }),
      updatePartner: (partial) => {
        const current = get().partnerUser;
        if (!current) return;
        set({ partnerUser: { ...current, partner: { ...current.partner, ...partial } } });
      },
      clear: () => set({ partnerUser: null, token: null, refreshToken: null }),
    }),
    {
      name: 'bp_aliados_session',
      onRehydrateStorage: () => () => {
        useAuth.setState({ hasHydrated: true });
      },
    }
  )
);
