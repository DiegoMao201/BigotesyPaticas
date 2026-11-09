/**
 * Avisos push al celular (8-nov-2026): llegan aunque la app esté cerrada.
 * En la app de Android (TWA) Chrome entrega la notificación a nombre de la app.
 */
const BASE = '/api/v1/portal/notifications/push';

const aBytes = (b64: string) => {
  const s = atob(b64.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((b64.length + 3) % 4));
  return Uint8Array.from(s, (c) => c.charCodeAt(0));
};

export type EstadoPush = 'no-soportado' | 'bloqueado' | 'activo' | 'apagado';

export function pushSoportado() {
  return typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
}

export async function estadoPush(): Promise<EstadoPush> {
  if (!pushSoportado()) return 'no-soportado';
  if (Notification.permission === 'denied') return 'bloqueado';
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = await reg?.pushManager.getSubscription();
  return sub && Notification.permission === 'granted' ? 'activo' : 'apagado';
}

function nombreEquipo() {
  const ua = navigator.userAgent;
  if (/Android/.test(ua)) return 'Android';
  if (/iPhone|iPad/.test(ua)) return 'iPhone';
  return 'Computador';
}

/** Pide permiso (si hace falta), suscribe este celular y lo registra en la API. */
export async function activarPush(): Promise<EstadoPush> {
  if (!pushSoportado()) return 'no-soportado';
  const permiso = await Notification.requestPermission();
  if (permiso !== 'granted') return permiso === 'denied' ? 'bloqueado' : 'apagado';
  const { public_key } = await fetch(`${BASE}/config`).then((r) => r.json());
  if (!public_key) throw new Error('Los avisos aún no están activos');
  const reg = (await navigator.serviceWorker.getRegistration()) ?? (await navigator.serviceWorker.register('/sw.js'));
  await navigator.serviceWorker.ready;
  let sub = await reg.pushManager.getSubscription();
  if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: aBytes(public_key) });
  const r = await fetch(`${BASE}/subscribe`, {
    method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subscription: sub.toJSON(), equipo: nombreEquipo() }),
  });
  if (!r.ok) throw new Error('No pudimos activar los avisos');
  return 'activo';
}

export async function apagarPush() {
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = await reg?.pushManager.getSubscription();
  if (!sub) return;
  await fetch(`${BASE}/unsubscribe`, {
    method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ endpoint: sub.endpoint }),
  }).catch(() => {});
  await sub.unsubscribe();
}

export async function probarPush() {
  const r = await fetch(`${BASE}/test`, { method: 'POST', credentials: 'include' });
  return (await r.json()) as { enviados: number };
}
