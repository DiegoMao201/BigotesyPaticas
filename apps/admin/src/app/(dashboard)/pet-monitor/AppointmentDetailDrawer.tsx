'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  X, MessageCircle, Calendar, Clock, User, PawPrint, DollarSign,
  CheckCircle2, XCircle, CalendarClock, StickyNote,
} from 'lucide-react';
import { adminPortal } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { buildWhatsAppUrl } from '@/lib/phone';
import { DURACIONES } from './AgendaCitas';

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pending: { label: 'Pendiente', color: 'bg-blue-100 text-blue-700' },
  confirmed: { label: 'Confirmada', color: 'bg-green-100 text-green-700' },
  completed: { label: 'Completada', color: 'bg-gray-100 text-gray-600' },
  cancelled: { label: 'Cancelada', color: 'bg-red-100 text-red-700' },
};

const WORKFLOW_LABELS: Record<string, string> = {
  requested: 'Solicitada',
  confirmed: 'Confirmada',
  awaiting_customer_reschedule: 'Esperando que cliente elija nuevo horario',
  rescheduled: 'Reagendada',
  in_progress: 'En curso',
  completed: 'Completada',
  no_show: 'No asistió',
  cancelled: 'Cancelada',
};

const REASON_CATEGORIES = [
  { value: 'sin_disponibilidad', label: 'Sin disponibilidad en ese horario' },
  { value: 'cliente_solicito', label: 'El cliente lo pidió' },
  { value: 'imprevisto_tienda', label: 'Imprevisto de la tienda' },
  { value: 'otro', label: 'Otro motivo' },
];

interface Props {
  apptId: string;
  onClose: () => void;
  onRefreshList: () => void;
}

// Lo mismo que ve el cliente en bigotesypaticas.com/peluqueria: se trae a la tienda,
// se llega 20 minutos antes, la cita queda en firme con esta confirmación.
const DIRECCION_TIENDA = 'Samara Plaza Mall, Cl. 15 #3A-07, Local 2, Dosquebradas';
const MAPA_TIENDA = 'https://maps.google.com/?cid=8425398225613945586';

const SERVICE_LABELS: Record<string, string> = {
  grooming: 'baño y peluquería',
  'baño': 'baño',
};

/** Reagendar (29-sep-2026): día + solo las horas libres para la duración de la cita, sin
 * contar la cita misma. Sirve igual para citas del portal, la web o la tienda. */
function ElegirNuevoHorario({ apptId, fechaActual, duracionMin, valor, onElegir }: {
  apptId: string; fechaActual: string; duracionMin: number; valor: string; onElegir: (v: string) => void;
}) {
  const base = new Date(fechaActual);
  const [dia, setDia] = useState(
    `${base.getFullYear()}-${String(base.getMonth() + 1).padStart(2, '0')}-${String(base.getDate()).padStart(2, '0')}`,
  );
  const { data, isFetching } = useQuery({
    queryKey: ['admin-horas-libres', dia, duracionMin, apptId],
    queryFn: () => adminPortal.horasLibres(dia, duracionMin, apptId),
  });
  const hora12 = (t: string) => {
    const [h, m] = t.split(':').map(Number);
    return `${h > 12 ? h - 12 : h}:${String(m).padStart(2, '0')} ${h < 12 ? 'a. m.' : 'p. m.'}`;
  };
  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs font-semibold text-gray-600">Nuevo día</label>
      <input type="date" value={dia} onChange={(e) => { if (e.target.value) { setDia(e.target.value); onElegir(''); } }}
        className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-800" />
      <label className="text-xs font-semibold text-gray-600 flex items-center gap-2">
        Nueva hora (libres para {duracionMin / 60} h) {isFetching && <span className="text-gray-400">…</span>}
      </label>
      {data && data.starts.length === 0 ? (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">No hay espacio ese día para {duracionMin / 60} h. Prueba otro día.</p>
      ) : (
        <div className="grid grid-cols-4 gap-1.5 max-h-36 overflow-y-auto">
          {(data?.starts ?? []).map((t) => {
            const v = `${dia}T${t}`;
            return (
              <button key={t} type="button" onClick={() => onElegir(v)}
                className={`rounded-md border py-1.5 text-xs font-semibold ${valor === v ? 'border-teal-600 bg-teal-600 text-white' : 'border-gray-300 bg-white text-gray-700 hover:border-teal-400'}`}>
                {hora12(t)}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function AppointmentDetailDrawer({ apptId, onClose, onRefreshList }: Props) {
  const qc = useQueryClient();
  const [showReschedule, setShowReschedule] = useState(false);
  const [newDateTime, setNewDateTime] = useState('');
  const [reasonCategory, setReasonCategory] = useState(REASON_CATEGORIES[0].value);
  const [showCancel, setShowCancel] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [noteText, setNoteText] = useState('');
  const [duracion, setDuracion] = useState<number | null>(null);

  const { data: appt, isLoading } = useQuery({
    queryKey: ['appt-detail', apptId],
    queryFn: () => adminPortal.appointmentDetail(apptId),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['appt-detail', apptId] });
    qc.invalidateQueries({ queryKey: ['admin-agenda'] });
    qc.invalidateQueries({ queryKey: ['admin-pending-appointments'] });
    qc.invalidateQueries({ queryKey: ['admin-horas-libres'] });
    onRefreshList();
  };

  const statusMut = useMutation({
    mutationFn: (body: { status: string; cancel_reason?: string; duration_min?: number }) => adminPortal.updateAppointment(apptId, body),
    onSuccess: (_, vars) => {
      toast.success(`Cita → ${STATUS_LABELS[vars.status]?.label ?? vars.status}`);
      setShowCancel(false);
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const completeMut = useMutation({
    mutationFn: () => adminPortal.completeAppointment(apptId),
    onSuccess: () => { toast.success('Cita marcada como completada'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const noShowMut = useMutation({
    mutationFn: () => adminPortal.noShowAppointment(apptId),
    onSuccess: () => { toast.success('Cita marcada como "no asistió"'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const rescheduleMut = useMutation({
    mutationFn: async () => {
      const iso = new Date(newDateTime).toISOString();
      await adminPortal.rescheduleAppointment(apptId, {
        proposed_options: [iso],
        reason_category: reasonCategory,
        compensation_points: 0,
      });
      return adminPortal.confirmApptChoice(apptId, iso, 'admin');
    },
    onSuccess: () => {
      toast.success('Cita reagendada');
      setShowReschedule(false);
      setNewDateTime('');
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const notesMut = useMutation({
    mutationFn: () => adminPortal.updateApptNotes(apptId, noteText),
    onSuccess: () => { toast.success('Nota guardada'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  if (isLoading || !appt) {
    return (
      <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={onClose}>
        <div className="bg-white rounded-2xl p-8 shadow-2xl">
          <div className="h-8 w-8 rounded-full border-2 border-teal-200 border-t-teal-600 animate-spin mx-auto" />
        </div>
      </div>
    );
  }

  const statusInfo = STATUS_LABELS[appt.status] ?? { label: appt.status, color: 'bg-gray-100 text-gray-600' };
  const dt = new Date(appt.scheduled_at);
  const canManage = !['completed', 'cancelled'].includes(appt.status);

  const waLink = (() => {
    if (!appt.customer_phone) return null;
    const firstName = (appt.customer_name || '').split(' ')[0] || '';
    const fecha = dt.toLocaleDateString('es-CO', { day: 'numeric', month: 'long' });
    const hora = dt.toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' });
    const servicio = SERVICE_LABELS[appt.service_type] ?? appt.service_type;
    const mascota = appt.pet_name ? ` de ${appt.pet_name}` : '';
    const hola = `¡Hola${firstName ? ' ' + firstName : ''}! Te escribo de Bigotes y Paticas`;
    // El mensaje sigue a lo que hizo el admin: confirmar, reacomodar o cancelar (28-sep-2026)
    const llegada = new Date(dt.getTime() - 20 * 60 * 1000).toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' });
    const msg =
      appt.status === 'confirmed'
        ? `${hola}. ✅ Tu cita de ${servicio}${mascota} quedó confirmada para el ${fecha} a las ${hora}.\n\n📍 Trae a tu mascota a la tienda (no hacemos recogida): ${DIRECCION_TIENDA}.\n⏰ Por favor llega 20 minutos antes, a las ${llegada}.\n🗺️ Cómo llegar: ${MAPA_TIENDA}\n\nSi no puedes asistir, avísanos por aquí. ¡Te esperamos! 🐾`
        : appt.status === 'cancelled'
          ? `${hola}. Tuvimos que cancelar tu cita de ${servicio}${mascota} del ${fecha} a las ${hora}${appt.cancel_reason ? ` (${appt.cancel_reason})` : ''}. ¿Te buscamos otro horario?`
          : `${hola}. Recibimos tu solicitud de ${servicio}${mascota} para el ${fecha} a las ${hora}. ¿Nos confirmas que te queda bien ese horario? Te recuerdo que la mascota se trae a la tienda (no hacemos recogida) y que es bueno llegar 20 minutos antes.`;
    return { url: buildWhatsAppUrl(appt.customer_phone, msg), label:
      appt.status === 'confirmed' ? 'Avisar confirmación por WhatsApp'
        : appt.status === 'cancelled' ? 'Avisar cancelación por WhatsApp'
          : 'Escribir por WhatsApp para confirmar' };
  })();

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-xl bg-white z-50 shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-gray-50 shrink-0">
          <div>
            <p className="text-xs text-gray-500 mb-0.5">{appt.notes?.includes('Reservó en la web') ? 'Cita desde la web (sin cuenta)' : appt.notes?.includes('Agendada por el admin') ? 'Cita agendada por la tienda' : 'Cita del portal'}</p>
            <h2 className="font-bold text-gray-900 flex items-center gap-1.5">
              <User size={14} className="text-gray-400" /> {appt.customer_name ?? 'Cliente'}
            </h2>
            {appt.customer_phone && <p className="text-xs text-gray-500">{appt.customer_phone}</p>}
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-semibold px-3 py-1 rounded-full ${statusInfo.color}`}>{statusInfo.label}</span>
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-200 transition-colors">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
          {/* Fecha/hora grande */}
          <div className="bg-teal-50 border border-teal-100 rounded-2xl p-4">
            <div className="flex items-center gap-2 text-teal-800 font-bold text-lg">
              <Calendar size={18} />
              {dt.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })}
            </div>
            <div className="flex items-center gap-2 text-teal-700 font-semibold mt-1">
              <Clock size={16} />
              {dt.toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' })} · {appt.duration_min} min
            </div>
            <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
              <span className="flex items-center gap-1"><PawPrint size={13} /> {appt.pet_name ?? '—'}</span>
              <span>{SERVICE_LABELS[appt.service_type] ?? appt.service_type}</span>
              {appt.price != null && (
                <span className="flex items-center gap-1"><DollarSign size={13} /> {formatCurrency(appt.price)}</span>
              )}
            </div>
            {appt.workflow_status && appt.workflow_status !== appt.status && (
              <p className="text-xs text-teal-600 mt-2">Estado detallado: {WORKFLOW_LABELS[appt.workflow_status] ?? appt.workflow_status}</p>
            )}
            {appt.reschedule_reason_category && (
              <p className="text-xs text-gray-500 mt-1">Último reagendamiento: {appt.reschedule_reason_category}</p>
            )}
          </div>

          {/* WhatsApp */}
          {waLink && appt.status !== 'completed' && (
            <a
              href={waLink.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 py-2.5 rounded-xl font-bold text-white text-sm"
              style={{ backgroundColor: '#25D366' }}
            >
              <MessageCircle size={16} /> {waLink.label}
            </a>
          )}

          {/* Reagendar */}
          {canManage && (
            !showReschedule ? (
              <button
                onClick={() => setShowReschedule(true)}
                className="flex items-center justify-center gap-1.5 text-sm text-teal-700 border-2 border-dashed border-teal-200 rounded-xl py-2.5 hover:bg-teal-50 transition-colors"
              >
                <CalendarClock size={15} /> Reacomodar horario
              </button>
            ) : (
              <div className="bg-gray-50 rounded-xl p-3 flex flex-col gap-2">
                <ElegirNuevoHorario
                  apptId={apptId}
                  fechaActual={appt.scheduled_at}
                  duracionMin={appt.duration_min}
                  valor={newDateTime}
                  onElegir={setNewDateTime}
                />
                <label className="text-xs font-semibold text-gray-600">Motivo</label>
                <select
                  value={reasonCategory}
                  onChange={(e) => setReasonCategory(e.target.value)}
                  className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm bg-white"
                >
                  {REASON_CATEGORIES.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
                <div className="flex gap-2 mt-1">
                  <button
                    onClick={() => rescheduleMut.mutate()}
                    disabled={!newDateTime || rescheduleMut.isPending}
                    className="bg-teal-600 text-white rounded-lg px-3 py-1.5 text-sm font-semibold disabled:opacity-50"
                  >
                    Guardar nuevo horario
                  </button>
                  <button onClick={() => setShowReschedule(false)} className="text-sm text-gray-500 underline">Cancelar</button>
                </div>
              </div>
            )
          )}

          {/* Notas internas */}
          <div className="flex flex-col gap-2">
            <p className="text-xs font-semibold text-gray-500 flex items-center gap-1"><StickyNote size={12} /> Notas</p>
            {appt.notes && <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-2">{appt.notes}</p>}
            <textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Agregar o reemplazar la nota de esta cita…"
              rows={2}
              className="rounded-xl border border-gray-200 p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
            <button onClick={() => notesMut.mutate()} disabled={!noteText || notesMut.isPending}
              className="self-start bg-teal-600 text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50">
              Guardar nota
            </button>
          </div>

          {/* Actividad */}
          {appt.activity.length > 0 && (
            <div className="flex flex-col gap-2 pt-2 border-t">
              <p className="text-xs font-semibold text-gray-500">Actividad</p>
              {appt.activity.map((log, i) => (
                <div key={i} className="text-xs text-gray-500 bg-gray-50 rounded-lg p-2">
                  <span className="font-medium text-gray-700">{log.action.replace(/_/g, ' ')}</span>
                  {log.actor_name && ` · ${log.actor_name}`} · {new Date(log.created_at).toLocaleString('es-CO')}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer acciones */}
        <div className="border-t bg-gray-50 p-4 flex flex-col gap-2 shrink-0">
          {/* Duración real del servicio: bloquea esas horas en la web y el portal (29-sep-2026) */}
          {(appt.status === 'pending' || appt.status === 'confirmed') && (
            <div>
              <p className="mb-1 text-xs font-semibold text-gray-600">¿Cuánto se demora el servicio?</p>
              <div className="grid grid-cols-4 gap-1.5">
                {DURACIONES.map((o) => {
                  const activo = (duracion ?? appt.duration_min) === o.min;
                  return (
                    <button key={o.min} type="button" onClick={() => setDuracion(o.min)}
                      className={`rounded-lg border py-2 text-sm font-semibold ${activo ? 'border-teal-600 bg-teal-600 text-white' : 'border-gray-300 bg-white text-gray-700 hover:border-teal-400'}`}>
                      {o.label}
                    </button>
                  );
                })}
              </div>
              {appt.status === 'confirmed' && duracion != null && duracion !== appt.duration_min && (
                <button
                  onClick={() => statusMut.mutate({ status: 'confirmed', duration_min: duracion }, { onSuccess: () => setDuracion(null) })}
                  disabled={statusMut.isPending}
                  className="mt-2 w-full rounded-xl bg-teal-600 py-2 text-sm font-bold text-white disabled:opacity-50"
                >
                  Guardar duración ({DURACIONES.find((o) => o.min === duracion)?.label})
                </button>
              )}
            </div>
          )}
          {appt.status === 'pending' && (
            <div className="flex gap-2">
              <button
                onClick={() => statusMut.mutate({ status: 'confirmed', duration_min: duracion ?? appt.duration_min })}
                disabled={statusMut.isPending}
                className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl font-bold text-white text-sm bg-green-600 disabled:opacity-50"
              >
                <CheckCircle2 size={15} /> Confirmar ({DURACIONES.find((o) => o.min === (duracion ?? appt.duration_min))?.label ?? `${appt.duration_min} min`})
              </button>
              {!showCancel ? (
                <button onClick={() => setShowCancel(true)} className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl font-bold text-red-600 border-2 border-red-200 text-sm">
                  <XCircle size={15} /> Cancelar
                </button>
              ) : null}
            </div>
          )}
          {appt.status === 'confirmed' && dt > new Date() && (
            <p className="text-center text-xs text-gray-500">Cita confirmada. "Completar" aparece cuando llegue la hora de la cita.</p>
          )}
          {appt.status === 'confirmed' && dt <= new Date() && (
            <div className="flex gap-2">
              <button
                onClick={() => completeMut.mutate()}
                disabled={completeMut.isPending}
                className="flex-1 py-2.5 rounded-xl font-bold text-white text-sm bg-teal-600 disabled:opacity-50"
              >
                ✅ Completar
              </button>
              <button
                onClick={() => noShowMut.mutate()}
                disabled={noShowMut.isPending}
                className="flex-1 py-2.5 rounded-xl font-bold text-gray-600 border-2 border-gray-200 text-sm disabled:opacity-50"
              >
                No asistió
              </button>
            </div>
          )}
          {showCancel && (
            <div className="flex gap-2 items-center">
              <input
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="Motivo de cancelación..."
                className="flex-1 rounded-lg border border-red-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
              />
              <button
                onClick={() => statusMut.mutate({ status: 'cancelled', cancel_reason: cancelReason })}
                disabled={!cancelReason || statusMut.isPending}
                className="bg-red-500 text-white rounded-lg px-3 py-1.5 text-sm font-semibold disabled:opacity-50"
              >
                Confirmar
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
