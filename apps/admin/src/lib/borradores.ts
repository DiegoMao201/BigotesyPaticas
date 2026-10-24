'use client';

/**
 * Borradores: lo que el usuario lleva a medio hacer en una pantalla sobrevive a
 * cambiar de pantalla, recargar o cerrar la pestaña.
 *
 * Diego (24-oct-2026): "imagínate haciendo una compra manual de 10 artículos, me
 * llega un cliente y me salgo a facturarle y se pierde todo lo que llevo". Cada
 * pantalla guardaba su trabajo en useState: al navegar, Next desmonta la página y
 * el estado se va. El aviso de pedidos pendientes (router.push a /pet-monitor)
 * hacía lo mismo sin que él tocara nada.
 *
 * useBorrador(clave, inicial) se usa igual que useState. La clave lleva el prefijo
 * de la ruta ("pos:carrito", "compras:manual") y con eso el menú lateral marca
 * las pantallas que tienen algo pendiente.
 */
import { useCallback, useSyncExternalStore } from 'react';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Entrada = { valor: unknown; vacio: boolean; at: number };

interface Borradores {
  b: Record<string, Entrada>;
  poner: (clave: string, valor: unknown, vacio: boolean) => void;
  quitar: (prefijo: string) => void;
}

const SIETE_DIAS = 7 * 24 * 3600 * 1000;

export const useBorradores = create<Borradores>()(
  persist(
    (set) => ({
      b: {},
      poner: (clave, valor, vacio) =>
        set((s) => ({ b: { ...s.b, [clave]: { valor, vacio, at: Date.now() } } })),
      // quita la clave exacta y todas las que empiezan por "prefijo:"
      quitar: (prefijo) =>
        set((s) => ({
          b: Object.fromEntries(
            Object.entries(s.b).filter(([k]) => k !== prefijo && !k.startsWith(`${prefijo}:`)),
          ),
        })),
    }),
    {
      name: 'bp_admin_borradores',
      // un borrador de hace más de una semana ya no es "lo que estaba haciendo"
      merge: (guardado, actual) => {
        const b = ((guardado as Partial<Borradores>)?.b ?? {}) as Record<string, Entrada>;
        const vivos = Object.fromEntries(Object.entries(b).filter(([, e]) => Date.now() - e.at < SIETE_DIAS));
        return { ...actual, b: vivos };
      },
    },
  ),
);

type Set<T> = (v: T | ((previo: T) => T)) => void;

const nada = () => () => {};
/** false en el servidor y durante la hidratación; true después. Evita el "el HTML no
 *  coincide" de React: el servidor no conoce el localStorage del navegador. */
function useEnCliente(): boolean {
  return useSyncExternalStore(nada, () => true, () => false);
}

export function useBorrador<T>(clave: string, inicial: T): [T, Set<T>] {
  const enCliente = useEnCliente();
  const guardado = useBorradores((s) => s.b[clave]);
  const poner = useBorradores((s) => s.poner);
  const valor = !enCliente || guardado === undefined ? inicial : (guardado.valor as T);
  const inicialJson = JSON.stringify(inicial);

  const set = useCallback<Set<T>>(
    (v) => {
      const e = useBorradores.getState().b[clave];
      const previo = e === undefined ? (JSON.parse(inicialJson) as T) : (e.valor as T);
      const nuevo = typeof v === 'function' ? (v as (p: T) => T)(previo) : v;
      poner(clave, nuevo, JSON.stringify(nuevo) === inicialJson);
    },
    [clave, inicialJson, poner],
  );

  return [valor, set];
}

/** Borra todos los borradores de una pantalla o de un formulario ("pos", "compras:manual"). */
export function descartarBorrador(prefijo: string) {
  useBorradores.getState().quitar(prefijo);
}

/** ¿Hay algo a medio hacer bajo este prefijo? Ignora campos que siguen en su valor inicial. */
export function useHayBorrador(prefijo: string): boolean {
  const enCliente = useEnCliente();
  const hay = useBorradores((s) =>
    Object.entries(s.b).some(([k, e]) => (k === prefijo || k.startsWith(`${prefijo}:`)) && !e.vacio),
  );
  return enCliente && hay;
}
