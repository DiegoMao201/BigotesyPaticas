/** Promesa de entrega que se puede cumplir, según la hora de Bogotá: la tienda
 *  entrega L-S de 10:00 a 19:00. Antes de las 17:00 de un día hábil, "llega hoy". */
export function promesaEntrega(ahora = new Date()): string {
  const bog = new Date(ahora.toLocaleString('en-US', { timeZone: 'America/Bogota' }));
  const dia = bog.getDay();
  const hora = bog.getHours();
  if (dia !== 0 && hora < 17) return 'Llega hoy';
  // siguiente día hábil (domingo no se entrega)
  const sig = new Date(bog);
  do sig.setDate(sig.getDate() + 1); while (sig.getDay() === 0);
  const diff = Math.round((sig.getTime() - bog.getTime()) / 86_400_000);
  return diff <= 1 ? 'Llega mañana' : `Llega el ${sig.toLocaleDateString('es-CO', { weekday: 'long' })}`;
}
