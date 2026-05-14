'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from './api';
import { clearAuth } from './api';

interface AuthState {
  user: User | null;
  token: string | null;
  setSession: (user: User, token: string) => void;
  clear: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setSession: (user, token) => set({ user, token }),
      clear: () => {
        clearAuth();
        set({ user: null, token: null });
      },
    }),
    { name: 'bp_admin_session' },
  ),
);
