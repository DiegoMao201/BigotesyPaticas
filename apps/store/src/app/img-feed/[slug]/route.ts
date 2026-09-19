/**
 * /img-feed/[slug].jpg — la foto del producto sobre un lienzo blanco de 1000x1000.
 *
 * POR QUÉ EXISTE. El 18-sep-2026 medimos las 520 imágenes del catálogo: solo 14
 * llegaban a 500 px por su lado menor, 370 se quedaban entre 250 y 499, y 136 no
 * pasaban de 250. Google empezó a rechazarlas con "Imagen demasiado pequeña —
 * actualiza la imagen para que tenga al menos 500x500 píxeles", y lo iba haciendo
 * por tandas, así que el problema no eran los 11 productos del informe: era casi
 * todo el catálogo cayendo en cámara lenta.
 *
 * Re-fotografiar 506 productos no es viable. Lo que sí resuelve el requisito sin
 * mentirle a nadie es centrar la foto real sobre un lienzo blanco del tamaño que
 * Google pide. El fondo blanco de relleno está permitido; lo que no se puede es
 * añadir marcos, logos ni texto promocional, y aquí no se añade nada.
 *
 * LA REGLA DE LOS 2x. Se amplía la foto como máximo al doble. Más que eso no
 * agrega información: solo emborrona. Las fotos de 300-500 px (la mayor parte del
 * catálogo) llegan al lienzo completo y se ven bien; las diminutas quedan nítidas
 * pero pequeñas y centradas, que es preferible a un borrón a pantalla completa.
 * Esas siguen mereciendo una foto de verdad algún día.
 *
 * SEGURIDAD. El slug es lo único que entra, y se valida: la URL de origen se
 * construye aquí contra el CDN, nunca se acepta una URL del exterior.
 */

import sharp from 'sharp';

export const revalidate = 604800; // una semana: la foto de un producto no cambia

const CDN = 'https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/products';
const LIENZO = 1000;
const MAX_AMPLIACION = 2;

/** Solo minúsculas, números y guiones: es un slug, no una ruta. */
function slugValido(s: string): boolean {
  return /^[a-z0-9][a-z0-9-]{0,120}$/.test(s);
}

export async function GET(
  _req: Request,
  { params }: { params: { slug: string } },
) {
  const slug = params.slug.replace(/\.(jpg|jpeg|webp|png)$/i, '');
  const origen = `${CDN}/${slug}/main.webp`;

  if (!slugValido(slug)) {
    return new Response('slug no válido', { status: 400 });
  }

  try {
    const res = await fetch(origen, { next: { revalidate: 604800 } });
    if (!res.ok) return Response.redirect(origen, 302);

    const entrada = Buffer.from(await res.arrayBuffer());
    const meta = await sharp(entrada).metadata();
    if (!meta.width || !meta.height) return Response.redirect(origen, 302);

    const escala = Math.min(MAX_AMPLIACION, LIENZO / Math.max(meta.width, meta.height));
    const w = Math.max(1, Math.round(meta.width * escala));
    const h = Math.max(1, Math.round(meta.height * escala));

    const salida = await sharp(entrada)
      .resize(w, h, { kernel: 'lanczos3' })
      // Un PNG con transparencia se vuelve negro al pasar a JPEG si no se aplana.
      .flatten({ background: '#ffffff' })
      .extend({
        top: Math.floor((LIENZO - h) / 2),
        bottom: Math.ceil((LIENZO - h) / 2),
        left: Math.floor((LIENZO - w) / 2),
        right: Math.ceil((LIENZO - w) / 2),
        background: '#ffffff',
      })
      .jpeg({ quality: 88, progressive: true })
      .toBuffer();

    return new Response(new Uint8Array(salida), {
      headers: {
        'Content-Type': 'image/jpeg',
        'Cache-Control': 'public, max-age=86400, s-maxage=604800, stale-while-revalidate=2592000',
      },
    });
  } catch {
    // Antes que quedarnos sin imagen en el feed, la original del CDN.
    return Response.redirect(origen, 302);
  }
}
