'use client';

/**
 * Punto de equilibrio: cuánto hay que vender para no perder plata.
 *
 * Diego (5-oct-2026): *"necesito afinar mucho el informe de ventas, de dónde sale
 * el presupuesto diario, que tengamos claridad de cómo vamos, para dónde vamos y
 * cuál es nuestro punto de equilibrio con los gastos promedios mensuales. Un admin
 * inteligente es una buena administración"*.
 *
 * Toda la pantalla gira alrededor de UN número —el presupuesto diario— porque es el
 * único que sirve para decidir hoy. El resto está para que ese número se pueda
 * comprobar en vez de creer: de dónde salen los gastos, de dónde sale el margen, y
 * qué parte del gasto no está clasificada y por tanto no se puede analizar.
 */

import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, Calculator, TrendingDown, TrendingUp } from 'lucide-react';
import { api } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

interface Equilibrio {
  meses_analizados: number;
  gasto_mensual_promedio: number;
  gasto_por_categoria: { categoria: string; total: number; mensual: number }[];
  ventas_mes_actual: number;
  venta_diaria_actual: number;
  margen_bruto_pct: number;
  ventas_90d: number;
  costo_90d: number;
  punto_equilibrio_mensual: number;
  punto_equilibrio_diario: number;
  dias_habiles_mes: number;
  sobre_equilibrio: number;
  estado: string;
  alerta_sin_categoria: number;
}

const SEMAFORO: Record<string, { txt: string; cls: string; detalle: string }> = {
  sano: {
    txt: 'Vas bien',
    cls: 'bg-emerald-50 border-emerald-300 text-emerald-900',
    detalle: 'Las ventas cubren los gastos con holgura.',
  },
  ajustado: {
    txt: 'Ajustado',
    cls: 'bg-amber-50 border-amber-300 text-amber-900',
    detalle:
      'Cubres los gastos, pero con poco margen. Un mes flojo o un gasto imprevisto te cruza la línea.',
  },
  en_perdida: {
    txt: 'Por debajo del equilibrio',
    cls: 'bg-rose-50 border-rose-300 text-rose-900',
    detalle: 'Las ventas del mes no alcanzan a cubrir los gastos.',
  },
  sin_datos: {
    txt: 'Faltan datos',
    cls: 'bg-gray-50 border-gray-300 text-gray-700',
    detalle: 'No hay suficiente información de costos para calcular el margen.',
  },
};

export default function EquilibrioPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['punto-equilibrio'],
    queryFn: () => api<Equilibrio>('/v1/expenses/punto-equilibrio'),
  });

  if (isLoading)
    return (
      <div className="p-8 text-center text-muted-foreground">Calculando con tus datos…</div>
    );
  if (!data) return <div className="p-8 text-muted-foreground">No se pudo calcular.</div>;

  const sem = SEMAFORO[data.estado] ?? SEMAFORO.sin_datos;
  const falta = data.punto_equilibrio_diario - data.venta_diaria_actual;
  const pct = data.punto_equilibrio_diario
    ? Math.min(200, (data.venta_diaria_actual / data.punto_equilibrio_diario) * 100)
    : 0;

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-[#0d4a45] flex items-center gap-2">
          <Calculator className="h-6 w-6" /> Punto de equilibrio
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Cuánto hay que vender para no perder plata. Calculado con tus gastos de los
          últimos {data.meses_analizados} meses y tu margen real.
        </p>
      </div>

      {/* EL NÚMERO. Todo lo demás existe para explicarlo. */}
      <div className="bg-white rounded-2xl shadow-sm p-6 text-center">
        <p className="text-sm font-semibold uppercase tracking-wider text-gray-400">
          Presupuesto diario mínimo
        </p>
        <p className="mt-1 text-5xl font-bold text-[#187f77] tabular-nums">
          {formatCurrency(data.punto_equilibrio_diario)}
        </p>
        <p className="mt-2 text-sm text-gray-500">
          Por debajo de esto, el día costó dinero
        </p>

        <div className="mt-5">
          <div className="flex justify-between text-xs font-medium mb-1.5">
            <span className="text-gray-500">Hoy vendes</span>
            <span className={falta > 0 ? 'text-rose-600' : 'text-emerald-600'}>
              {formatCurrency(data.venta_diaria_actual)} / día
            </span>
          </div>
          <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${falta > 0 ? 'bg-rose-400' : 'bg-emerald-500'}`}
              style={{ width: `${Math.max(3, Math.min(100, pct))}%` }}
            />
          </div>
          <p className="mt-2 text-sm">
            {falta > 0 ? (
              <span className="text-rose-700 font-semibold">
                Te faltan {formatCurrency(falta)} al día
              </span>
            ) : (
              <span className="text-emerald-700 font-semibold">
                Vas {formatCurrency(-falta)} por encima cada día
              </span>
            )}
          </p>
        </div>
      </div>

      <div className={`rounded-2xl border-2 p-4 ${sem.cls}`}>
        <p className="font-bold flex items-center gap-2">
          {data.estado === 'en_perdida' ? <TrendingDown className="h-5 w-5" /> : <TrendingUp className="h-5 w-5" />}
          {sem.txt}
        </p>
        <p className="mt-1 text-sm leading-relaxed">{sem.detalle}</p>
        <p className="mt-2 text-sm">
          Este mes vas <strong>{formatCurrency(Math.abs(data.sobre_equilibrio))}</strong>{' '}
          {data.sobre_equilibrio >= 0 ? 'por encima' : 'por debajo'} del equilibrio
          {data.ventas_mes_actual > 0 && (
            <> · {((data.sobre_equilibrio / data.ventas_mes_actual) * 100).toFixed(1)}% de lo vendido</>
          )}
          .
        </p>
      </div>

      {/* DE DÓNDE SALE EL NÚMERO. Un dato que no se puede comprobar no se usa. */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="bg-white rounded-2xl shadow-sm p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">
            Tu margen bruto
          </p>
          <p className="mt-1 text-3xl font-bold text-[#0d4a45]">{data.margen_bruto_pct}%</p>
          <p className="mt-2 text-xs text-gray-500 leading-relaxed">
            De cada $100.000 que vendes te quedan{' '}
            <strong>{formatCurrency(data.margen_bruto_pct * 1000)}</strong> para pagar
            todo lo demás. Sale de {formatCurrency(data.ventas_90d)} vendidos en 90 días
            menos {formatCurrency(data.costo_90d)} que costó esa mercancía.
          </p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">
            Gastos del mes
          </p>
          <p className="mt-1 text-3xl font-bold text-[#0d4a45]">
            {formatCurrency(data.gasto_mensual_promedio)}
          </p>
          <p className="mt-2 text-xs text-gray-500 leading-relaxed">
            Promedio de los últimos {data.meses_analizados} meses completos. El mes en
            curso no cuenta: está a medias y haría parecer que necesitas vender menos.
          </p>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm p-5">
        <p className="font-bold text-sm mb-3">En qué se va el dinero cada mes</p>
        <div className="space-y-2">
          {data.gasto_por_categoria.map((c) => {
            const p = data.gasto_mensual_promedio
              ? (c.mensual / data.gasto_mensual_promedio) * 100
              : 0;
            const difusa = c.categoria === 'Otros' || c.categoria === 'Sin categoría';
            return (
              <div key={c.categoria}>
                <div className="flex justify-between text-sm">
                  <span className={difusa ? 'text-amber-700 font-medium' : ''}>
                    {c.categoria} {difusa && '⚠️'}
                  </span>
                  <span className="tabular-nums font-medium">
                    {formatCurrency(c.mensual)}{' '}
                    <span className="text-gray-400 text-xs">({p.toFixed(0)}%)</span>
                  </span>
                </div>
                <div className="h-1.5 bg-gray-100 rounded-full mt-1 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${difusa ? 'bg-amber-400' : 'bg-[#187f77]'}`}
                    style={{ width: `${Math.max(2, p)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* Lo que no está clasificado no se puede analizar, y conviene saberlo ANTES
            de confiar en el número, no después. */}
        {data.alerta_sin_categoria > 0 && (
          <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
            <p className="font-semibold flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4" />
              {formatCurrency(data.alerta_sin_categoria)} al mes sin clasificar
            </p>
            <p className="mt-1 leading-relaxed">
              Es{' '}
              {data.gasto_mensual_promedio
                ? ((data.alerta_sin_categoria / data.gasto_mensual_promedio) * 100).toFixed(0)
                : 0}
              % de tu gasto en &ldquo;Otros&rdquo;. Sabes cuánto gastas, pero no en qué.
              Clasificarlo es lo que convierte este informe en una herramienta para
              decidir dónde recortar.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
