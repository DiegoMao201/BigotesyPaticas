'use client';

/**
 * La pantalla donde alguien decide si teclea su tarjeta.
 *
 * Todo lo que hay aquí responde a esa frase. Lo que genera confianza no es escribir
 * "sitio seguro" ni poner un candado dibujado: es que se vea **a quién le está
 * pagando** —el nombre real, la dirección del local, el teléfono de siempre, la
 * calificación de Google— y que el resumen cuadre al peso con lo que pidió.
 *
 * Y el monto NO se calcula aquí. Llega firmado desde el servidor, que lo sacó de los
 * precios de la base. Esta página lo muestra y se lo pasa a Bold; si hiciera una
 * sola cuenta, la firma dejaría de cuadrar y el cobro sería rechazado sin más
 * explicación.
 */

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Clock, MapPin, Phone, ShieldCheck, Star } from 'lucide-react';
import { BotonBold, type DatosBold } from '@/components/pago/BotonBold';
import { BUSINESS_INFO } from '@/lib/business-info';
import { formatCurrency } from '@/lib/utils';

type Cobro = {
  ok: boolean;
  motivo?: string | null;
  estado?: string;
  referencia?: string;
  amount?: number;
  currency?: string;
  integrity_signature?: string;
  identity_key?: string;
  expira?: string | null;
  items?: { nombre: string; cantidad: number; subtotal: number }[];
  subtotal?: number;
  envio?: number;
};

export function PaginaDePago({ referencia }: { referencia: string }) {
  const [cobro, setCobro] = useState<Cobro | null>(null);
  const [fallo, setFallo] = useState(false);

  useEffect(() => {
    fetch(`/api/v1/payments/${encodeURIComponent(referencia)}/cobro`)
      .then((r) => r.json())
      .then(setCobro)
      .catch(() => setFallo(true));
  }, [referencia]);

  if (fallo) {
    return <Aviso titulo="No pudimos cargar tu pedido" texto="Revisa tu conexión e intenta de nuevo, o escríbenos por WhatsApp." />;
  }
  if (!cobro) {
    return <Aviso titulo="Cargando tu pedido…" texto="Un momento, por favor." />;
  }

  if (!cobro.ok) {
    const motivos: Record<string, { t: string; d: string }> = {
      paid: { t: 'Este pedido ya está pagado', d: 'No tienes que pagar otra vez. Ya lo estamos alistando.' },
      vencido: { t: 'El enlace de pago venció', d: 'Pasó el tiempo para pagarlo. Escríbenos y lo armamos de nuevo en un minuto.' },
      expired: { t: 'El enlace de pago venció', d: 'Pasó el tiempo para pagarlo. Escríbenos y lo armamos de nuevo en un minuto.' },
      failed: { t: 'El pago anterior no se completó', d: 'Escríbenos y te mandamos un enlace nuevo enseguida.' },
      'no existe': { t: 'No encontramos este pedido', d: 'Revisa el enlace, o escríbenos y lo buscamos por tu nombre.' },
    };
    const m = motivos[cobro.motivo ?? ''] ?? motivos['no existe'];
    return <Aviso titulo={m.t} texto={m.d} />;
  }

  const datos: DatosBold = {
    order_reference: cobro.referencia!,
    amount: cobro.amount!,
    currency: cobro.currency || 'COP',
    integrity_signature: cobro.integrity_signature!,
    identity_key: cobro.identity_key!,
  };
  const retorno =
    typeof window !== 'undefined'
      ? `${window.location.origin}/pedido/confirmado?ref=${encodeURIComponent(referencia)}`
      : '';

  return (
    <div className="min-h-[85vh] bg-gradient-to-b from-[#f2fbfa] to-white py-10">
      <div className="container-tight max-w-lg">
        {/* Quién cobra. Va primero, antes que el monto: la pregunta que se hace
            cualquiera antes de pagar es "¿a quién le estoy dando mi tarjeta?". */}
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-[#187f77]">
            Pago seguro
          </p>
          <h1 className="mt-1 font-display text-2xl font-bold text-[#0d4a45]">
            Bigotes y Paticas
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">Tienda de mascotas · Dosquebradas</p>
          <div className="mt-3 flex items-center justify-center gap-1.5 text-sm">
            <Star className="h-4 w-4 fill-[#f5a641] text-[#f5a641]" aria-hidden="true" />
            <span className="font-semibold">{BUSINESS_INFO.rating.value}</span>
            <span className="text-muted-foreground">en Google</span>
          </div>
        </div>

        {/* El resumen. Tiene que cuadrar al peso con lo que pidió, o se abandona. */}
        <div className="mt-7 rounded-3xl border border-border bg-white p-6 shadow-sm">
          <h2 className="font-display text-base font-bold text-[#0d4a45]">Tu pedido</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {(cobro.items ?? []).map((i, n) => (
              <li key={n} className="flex items-start justify-between gap-3">
                <span className="text-muted-foreground">
                  {i.nombre} <span className="opacity-70">×{i.cantidad}</span>
                </span>
                <span className="shrink-0 tabular-nums">{formatCurrency(i.subtotal)}</span>
              </li>
            ))}
          </ul>
          {/* EL DESGLOSE, NO SOLO EL TOTAL. Un total a secas obliga a confiar;
              un desglose se puede comprobar. Y el domicilio es justo el número
              que la gente quiere ver antes de teclear la tarjeta. */}
          <div className="mt-4 space-y-1.5 border-t border-border pt-4 text-sm">
            <div className="flex justify-between text-muted-foreground">
              <span>Productos</span>
              <span className="tabular-nums">{formatCurrency(cobro.subtotal ?? 0)}</span>
            </div>
            <div className="flex justify-between text-muted-foreground">
              <span>Domicilio</span>
              <span className="tabular-nums">
                {(cobro.envio ?? 0) > 0 ? (
                  formatCurrency(cobro.envio ?? 0)
                ) : (
                  <span className="font-semibold text-[#187f77]">Gratis 🎉</span>
                )}
              </span>
            </div>
          </div>
          <div className="mt-3 flex items-end justify-between border-t border-border pt-3">
            <span className="font-semibold">Total a pagar</span>
            <span className="font-display text-2xl font-bold tabular-nums text-[#187f77]">
              {formatCurrency(cobro.amount ?? 0)}
            </span>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
            Entrega en Pereira y Dosquebradas, el mismo día. No hay cobros
            adicionales: este es el valor final.
          </p>

          <div className="mt-6">
            <BotonBold
              datos={datos}
              urlRetorno={retorno}
              descripcion={`Pedido ${referencia} · Bigotes y Paticas`}
            />
          </div>

          <p className="mt-4 flex items-start gap-2 text-xs leading-relaxed text-muted-foreground">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#187f77]" aria-hidden="true" />
            <span>
              El pago lo procesa <strong>Bold</strong>. Tus datos de tarjeta viajan
              directo a la pasarela: nosotros nunca los vemos ni los guardamos.
            </span>
          </p>
        </div>

        {/* Lo institucional: dirección real, horario real, teléfono real. */}
        <div className="mt-5 rounded-3xl border border-border bg-white/70 p-5 text-sm">
          <p className="font-semibold text-[#0d4a45]">¿Dudas antes de pagar?</p>
          <ul className="mt-3 space-y-2 text-muted-foreground">
            <li className="flex items-start gap-2">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-[#187f77]" aria-hidden="true" />
              <span>{BUSINESS_INFO.address.streetAddress}, {BUSINESS_INFO.address.addressLocality}</span>
            </li>
            <li className="flex items-start gap-2">
              <Clock className="mt-0.5 h-4 w-4 shrink-0 text-[#187f77]" aria-hidden="true" />
              <span>Lunes a sábado, 10:00 a. m. – 7:00 p. m.</span>
            </li>
            <li className="flex items-start gap-2">
              <Phone className="mt-0.5 h-4 w-4 shrink-0 text-[#187f77]" aria-hidden="true" />
              <a href={`https://wa.me/${BUSINESS_INFO.whatsapp}`} className="font-medium text-[#187f77] underline">
                {BUSINESS_INFO.phoneDisplay} · WhatsApp
              </a>
            </li>
          </ul>
        </div>

        <p className="mt-5 text-center font-mono text-[11px] text-muted-foreground">
          {referencia}
        </p>
      </div>
    </div>
  );
}

function Aviso({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <div className="container-tight min-h-[70vh] py-20">
      <div className="mx-auto max-w-md rounded-3xl border border-border bg-card p-8 text-center">
        <h1 className="font-display text-xl font-bold text-[#0d4a45]">{titulo}</h1>
        <p className="mt-3 text-sm text-muted-foreground">{texto}</p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Link
            href="/categorias/todos"
            className="rounded-xl bg-[#187f77] px-5 py-3 text-sm font-semibold text-white"
          >
            Ir a la tienda
          </Link>
          <a
            href="https://wa.me/573206876633"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-xl border border-border px-5 py-3 text-sm font-semibold"
          >
            Escribirnos
          </a>
        </div>
      </div>
    </div>
  );
}
