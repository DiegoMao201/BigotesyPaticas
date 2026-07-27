import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCOP(amount: number): string {
  return '$' + Math.round(amount).toLocaleString('es-CO');
}

const DAY_LABELS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

export function dayLabel(dayOfWeek: number): string {
  return DAY_LABELS[dayOfWeek] ?? '?';
}

const DAY_LABELS_SHORT = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

export function dayLabelShort(dayOfWeek: number): string {
  return DAY_LABELS_SHORT[dayOfWeek] ?? '?';
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString('es-CO', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' });
}
