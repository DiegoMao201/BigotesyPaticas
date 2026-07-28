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
//
// IMPORTANTE: `onRehydrateStorage` no puede referenciar el propio `useAuth`
// por nombre (p. ej. `useAuth.setState(...)`) — en el build minificado esa
// auto-referencia cayó en un TDZ real (`ReferenceError: Cannot access 'n'
// before initialization`) porque el callback corre en un microtask que a
// veces se dispara antes de que termine de asignarse el const `useAuth`.
// En su lugar, capturamos `set` directamente del closure del store.
let markHydrated: (() => void) | null = null;

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => {
      markHydrated = () => set({ hasHydrated: true });
      return {
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
      };
    },
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
      onRehydrateStorage: () => () => {
        markHydrated?.();
      },
    }
  )
);
