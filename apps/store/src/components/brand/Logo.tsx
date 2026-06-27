import Image from 'next/image';

interface LogoProps {
  size?: number;
  className?: string;
  priority?: boolean;
}

export function Logo({ size = 48, className = '', priority = false }: LogoProps) {
  return (
    <Image
      src="/icon.svg"
      alt="Bigotes y Paticas"
      width={size}
      height={size}
      className={className}
      priority={priority}
      unoptimized
    />
  );
}
