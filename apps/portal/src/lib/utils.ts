import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCOP(amount: number): string {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('es-CO', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'Hoy';
  if (diffDays === 1) return 'Mañana';
  if (diffDays === -1) return 'Ayer';
  if (diffDays > 0 && diffDays < 7) return `En ${diffDays} días`;
  if (diffDays < 0 && diffDays > -7) return `Hace ${Math.abs(diffDays)} días`;
  return formatDate(dateStr);
}

export function getSpeciesEmoji(species: string): string {
  const map: Record<string, string> = {
    perro: '🐶', dog: '🐶',
    gato: '🐱', cat: '🐱',
    conejo: '🐰', rabbit: '🐰',
    hamster: '🐹', hamster: '🐹',
    ave: '🐦', bird: '🐦',
    pez: '🐟', fish: '🐟',
  };
  return map[species.toLowerCase()] ?? '🐾';
}

export const WHATSAPP_NUMBER = '573206876633';

export function whatsappLink(message: string): string {
  return `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;
}
