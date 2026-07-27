'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { PartnerUserInfo } from './api';

interface AuthState {
  partnerUser: PartnerUserInfo | null;
  token: string | null;
  refreshToken: string | null;
  setSession: (partnerUser: PartnerUserInfo, token: string, refreshToken: string) => void;
  updatePartner: (partial: Partial<PartnerUserInfo['partner']>) => void;
  clear: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      partnerUser: null,
      token: null,
      refreshToken: null,
      setSession: (partnerUser, token, refreshToken) => set({ partnerUser, token, refreshToken }),
      updatePartner: (partial) => {
        const current = get().partnerUser;
        if (!current) return;
        set({ partnerUser: { ...current, partner: { ...current.partner, ...partial } } });
      },
      clear: () => set({ partnerUser: null, token: null, refreshToken: null }),
    }),
    { name: 'bp_aliados_session' }
  )
);
