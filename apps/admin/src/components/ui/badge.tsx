import { cn } from '@/lib/utils';

type Variant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'brand';

const VARIANTS: Record<Variant, string> = {
  default: 'bg-muted text-foreground',
  success: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  warning: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  danger: 'bg-red-500/15 text-red-700 dark:text-red-300',
  info: 'bg-blue-500/15 text-blue-700 dark:text-blue-300',
  neutral: 'bg-gray-500/15 text-gray-700 dark:text-gray-300',
  brand: 'bg-brand-500/15 text-brand-700 dark:text-brand-300',
};

export function Badge({
  children,
  variant = 'default',
  className,
}: {
  children: React.ReactNode;
  variant?: Variant;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold',
        VARIANTS[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
