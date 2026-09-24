/**
 * La nota y el número de reseñas de la ficha de Google, FRESCOS.
 *
 * Diego (24-sep-2026): *"esto ya cambió, mantenlo actualizado"*. Y tenía razón:
 * estaban escritas a mano como "28 reseñas" y la ficha ya iba por 30.
 *
 * Se leen del endpoint público de la tienda, que desde hoy publica el total REAL
 * que Google reporta (antes contaba solo las reseñas que cabían en su caché —5
 * como máximo— y publicaba 7 cuando había 30: malvendía el negocio por cuatro).
 *
 * Si la llamada falla NO se inventa un número: se devuelve null y quien llame
 * decide si esconder el dato. Un número inventado en la página es peor que
 * ninguno.
 */
export type FichaGoogle = { nota: number; resenas: number } | null;

export async function fichaGoogle(): Promise<FichaGoogle> {
  const base =
    process.env.API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    'https://bigotesypaticas.com/api';
  try {
    const r = await fetch(`${base}/v1/public/gbp-reviews?limit=1`, {
      next: { revalidate: 3600 },
    });
    if (!r.ok) return null;
    const d = (await r.json()) as { aggregate?: { avg?: number; count?: number } };
    const nota = d.aggregate?.avg;
    const resenas = d.aggregate?.count;
    if (typeof nota !== 'number' || typeof resenas !== 'number' || resenas < 1) return null;
    return { nota, resenas };
  } catch {
    return null;
  }
}
