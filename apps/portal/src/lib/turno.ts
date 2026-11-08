/**
 * UN SOLO AVISO POR VISITA (8-nov-2026). Un cliente nuevo que entraba al portal se
 * encontraba, uno tras otro: términos → "ayúdanos a encontrar mascotas" (ubicación) →
 * promo de peluquería → instalar la app → reseña de Google. Cinco ventanas antes de ver
 * un solo producto. Ahora cada aviso pide turno y solo uno sale por sesión; los demás
 * esperan a la próxima visita. Los términos van aparte porque son obligatorios, y
 * mientras no estén aceptados no sale ningún otro.
 */
const CLAVE = 'bp_aviso_de_esta_visita';

export function tomarTurno(nombre: string): boolean {
  try {
    const actual = sessionStorage.getItem(CLAVE);
    if (actual && actual !== nombre) return false;
    sessionStorage.setItem(CLAVE, nombre);
    return true;
  } catch {
    return true;
  }
}
