'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Pet } from './api';

interface PetState {
  activePetId: string | null;
  setActivePet: (id: string | null) => void;
  getActivePet: (pets: Pet[]) => Pet | null;
}

export const usePetStore = create<PetState>()(
  persist(
    (set, get) => ({
      activePetId: null,
      setActivePet: (id) => set({ activePetId: id }),
      getActivePet: (pets) => {
        const { activePetId } = get();
        if (!activePetId || pets.length === 0) return pets[0] ?? null;
        return pets.find((p) => p.id === activePetId) ?? pets[0];
      },
    }),
    { name: 'bp_portal_active_pet' }
  )
);

// Mapa de colores por tema de mascota
export const PET_THEME_COLORS: Record<string, { primary: string; light: string; dark: string; label: string }> = {
  teal:   { primary: '#187f77', light: '#edfaf9', dark: '#125e58', label: 'Teal' },
  coral:  { primary: '#e05252', light: '#fef2f2', dark: '#b91c1c', label: 'Coral' },
  amber:  { primary: '#f5a641', light: '#fff8ed', dark: '#b45309', label: 'Ámbar' },
  purple: { primary: '#7c3aed', light: '#f5f3ff', dark: '#5b21b6', label: 'Violeta' },
  pink:   { primary: '#db2777', light: '#fdf2f8', dark: '#9d174d', label: 'Rosa' },
  green:  { primary: '#16a34a', light: '#f0fdf4', dark: '#166534', label: 'Verde' },
};
