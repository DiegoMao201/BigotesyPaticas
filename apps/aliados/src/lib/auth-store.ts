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
      // `hasHydrated` NUNCA debe persistirse — si queda guardado como `false`
      // (ej. por un write que ocurre antes de que termine de hidratar), la
      // siguiente carga rehidrata ese `false` y la app queda bloqueada en
      // blanco para siempre, sin importar lo que haga onRehydrateStorage.
      partialize: (state) => ({
        partnerUser: state.partnerUser,
        token: state.token,
        refreshToken: state.refreshToken,
      }),
      onRehydrateStorage: () => (state, error) => {
        // eslint-disable-next-line no-console
        console.log('[DEBUG onRehydrateStorage fired]', { state, error });
        useAuth.setState({ hasHydrated: true });
      },
    }
  )
);
