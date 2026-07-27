import { cn } from '@/lib/utils';

type Variant = 'default' | 'success' | 'warning' | 'danger' | 'neutral';

const VARIANTS: Record<Variant, string> = {
  default: 'bg-primary-50 text-primary-700',
  success: 'bg-emerald-50 text-emerald-700',
  warning: 'bg-amber-50 text-amber-700',
  danger: 'bg-red-50 text-red-600',
  neutral: 'bg-gray-100 text-gray-600',
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
        'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold',
        VARIANTS[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
