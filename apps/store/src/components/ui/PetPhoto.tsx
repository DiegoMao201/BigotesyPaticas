import Image from 'next/image';

/**
 * Foto subida por un usuario (adopción, perdidos, encontrados) mostrada
 * COMPLETA, sin recortar: `object-contain` encima de una copia difuminada
 * de la misma imagen que rellena el contenedor, así una foto vertical de
 * celular en una tarjeta horizontal no pierde la cabeza del animal ni deja
 * barras vacías. El padre debe ser `relative` + `overflow-hidden` con alto.
 */
export function PetPhoto({
  src,
  alt,
  sizes,
  priority = false,
  className = '',
}: {
  src: string;
  alt: string;
  sizes: string;
  priority?: boolean;
  className?: string;
}) {
  return (
    <>
      <Image
        src={src}
        alt=""
        aria-hidden
        fill
        sizes={sizes}
        className="object-cover scale-110 blur-2xl opacity-60"
      />
      <Image
        src={src}
        alt={alt}
        fill
        priority={priority}
        sizes={sizes}
        className={`object-contain ${className}`.trim()}
      />
    </>
  );
}
