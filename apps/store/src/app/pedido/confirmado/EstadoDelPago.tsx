'use client';

/**
 * Pregunta al servidor cómo quedó el pago y lo muestra. Nunca lo deduce de la URL.
 *
 * POR QUÉ HAY QUE PREGUNTAR VARIAS VECES
 * Con tarjeta el pago se resuelve en segundos, pero con PSE el banco puede tardar:
 * el cliente vuelve aquí y el webhook todavía no ha llegado. Si mostráramos
 * "no pagado" de una vez, lo mandaríamos a pagar otra vez algo que ya pagó. Por eso
 * se pregunta cada 3 segundos durante 2 minutos y, mientras tanto, lo que se ve es
 * "estamos verificando", que es la verdad.
 *
 * Pasados los 2 minutos se deja de preguntar y se le dice que le avisamos por
 * WhatsApp: seguir preguntando para siempre castiga al servidor y no cambia nada,
 * porque la conciliación ya se encarga de rescatar el pago aunque nadie mire.
 */

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

const CADA_MS = 3000;
const HASTA_MS = 120_000;

type Estado = {
  encontrado: boolean;
  estado: string;
  referencia?: string;
  total?: number;
  definitivo?: boolean;
};

export function EstadoDelPago() {
  const params = useSearchParams();
  // El parámetro solo dice QUÉ preguntar. La respuesta la da el servidor.
  const referencia = params.get('bold-order-id') || params.get('ref') || '';

  const [estado, setEstado] = useState<Estado | null>(null);
  const [agotado, setAgotado] = useState(false);
  const desde = useRef(Date.now());

  const preguntar = useCallback(async () => {
    if (!referencia) return true;
    try {
      const r = await fetch(`/api/v1/payments/${encodeURIComponent(referencia)}/estado`);
      if (r.status === 429) return false; // frenado: se reintenta en el próximo ciclo
      const d: Estado = await r.json();
      setEstado(d);
      return Boolean(d.definitivo) || !d.encontrado;
    } catch {
      return false;
    }
  }, [referencia]);

  useEffect(() => {
    let vivo = true;
    let temporizador: ReturnType<typeof setTimeout>;

    const ciclo = async () => {
      const listo = await preguntar();
      if (!vivo) return;
      if (listo) return;
      if (Date.now() - desde.current > HASTA_MS) {
        setAgotado(true);
        return;
      }
      temporizador = setTimeout(ciclo, CADA_MS);
    };
    ciclo();

    return () => {
      vivo = false;
      clearTimeout(temporizador);
    };
  }, [preguntar]);

  if (!referencia) {
    return (
      <Mensaje
        icono="🐾"
        titulo="No encontramos tu pedido"
        texto="Este enlace no trae la referencia del pedido. Si acabas de pagar, escríbenos y lo buscamos."
      />
    );
  }

  if (!estado) {
    return <Mensaje icono="⏳" titulo="Consultando tu pago…" texto="Un momento, por favor." />;
  }

  if (!estado.encontrado) {
    return (
      <Mensaje
        icono="🔍"
        titulo="No encontramos ese pedido"
        texto="Revisa el enlace, o escríbenos por WhatsApp con tu nombre y te decimos cómo va."
      />
    );
  }

  const monto = estado.total ? `$${estado.total.toLocaleString('es-CO')}` : '';

  if (estado.estado === 'paid') {
    return (
      <Mensaje
        icono="✅"
        titulo="¡Pago confirmado!"
        texto={`Recibimos tu pago${monto ? ` de ${monto}` : ''}. Ya estamos alistando tu pedido y te escribimos por WhatsApp cuando salga para tu casa.`}
        referencia={estado.referencia}
        tono="bien"
      />
    );
  }

  if (estado.estado === 'failed') {
    return (
      <Mensaje
        icono="❌"
        titulo="El pago no se completó"
        texto="Tu banco no aprobó la transacción y no te cobramos nada. Puedes intentar con otro medio de pago o pedir contraentrega."
        referencia={estado.referencia}
        tono="mal"
      />
    );
  }

  if (estado.estado === 'expired') {
    return (
      <Mensaje
        icono="⌛"
        titulo="El pedido venció"
        texto="Pasó el tiempo para pagarlo. No te preocupes: escríbenos y lo armamos de nuevo en un minuto."
        referencia={estado.referencia}
      />
    );
  }

  // Sigue pendiente: ni se confirma ni se niega. Decir "no pagado" aquí mandaría a
  // pagar dos veces a quien ya pagó por PSE.
  return (
    <Mensaje
      icono="⏳"
      titulo={agotado ? 'Seguimos verificando tu pago' : 'Verificando tu pago…'}
      texto={
        agotado
          ? 'Tu banco se está tomando más de lo normal. No tienes que hacer nada: en cuanto se confirme te escribimos por WhatsApp. Si prefieres, escríbenos y lo revisamos contigo.'
          : 'Esto puede tardar unos segundos si pagaste por PSE. No cierres esta página.'
      }
      referencia={estado.referencia}
    />
  );
}

function Mensaje({
  icono,
  titulo,
  texto,
  referencia,
  tono,
}: {
  icono: string;
  titulo: string;
  texto: string;
  referencia?: string;
  tono?: 'bien' | 'mal';
}) {
  // El mensaje llega ESCRITO con la referencia. Quien escribe desde aquí lo hace
  // porque algo de su pago le preocupa; obligarle a teclear un código que no tiene
  // a mano es ponerle un obstáculo justo en ese momento. Y a quien atiende le llega
  // la pregunta con el dato que necesita para responder.
  const texto_wa = referencia
    ? `Hola! Acabo de pagar en la página. Mi pedido es ${referencia} 🐾`
    : 'Hola! Tengo una pregunta sobre mi pedido 🐾';
  const waUrl = `https://wa.me/573206876633?text=${encodeURIComponent(texto_wa)}`;
  const borde =
    tono === 'bien' ? 'border-teal-200 bg-teal-50' : tono === 'mal' ? 'border-red-200 bg-red-50' : 'border-border bg-card';
  return (
    <div className={`mx-auto max-w-lg rounded-3xl border p-8 text-center ${borde}`}>
      <div className="text-5xl" aria-hidden="true">
        {icono}
      </div>
      <h1 className="mt-4 font-display text-2xl font-bold text-[#0d4a45]">{titulo}</h1>
      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{texto}</p>
      {referencia && (
        <p className="mt-4 font-mono text-xs text-muted-foreground">
          Referencia: {referencia}
        </p>
      )}
      <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:justify-center">
        <Link
          href="/categorias/todos"
          className="rounded-xl bg-[#187f77] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#0d4a45]"
        >
          Seguir comprando
        </Link>
        <a
          href={waUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-xl border border-border px-5 py-3 text-sm font-semibold transition-colors hover:bg-muted"
        >
          Escribirnos por WhatsApp
        </a>
      </div>
    </div>
  );
}
