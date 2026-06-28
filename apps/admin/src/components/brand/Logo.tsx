import Image from 'next/image';

interface LogoProps {
  size?: number;
  className?: string;
  priority?: boolean;
  variant?: 'plain' | 'header' | 'footer' | 'hero';
}

export function Logo({ size = 56, className = '', priority = false, variant = 'plain' }: LogoProps) {
  const variantClasses: Record<string, string> = {
    plain: '',
    header: 'transition-all duration-300 drop-shadow-md hover:scale-105 hover:drop-shadow-2xl',
    footer: 'opacity-90',
    hero: '',
  };
  const cls = [variantClasses[variant], className].filter(Boolean).join(' ');
  return (
    <Image
      src="/icon.svg"
      alt="Bigotes y Paticas"
      width={size}
      height={size}
      priority={priority}
      className={cls}
      unoptimized
    />
  );
}
