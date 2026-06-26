'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, X, Check } from 'lucide-react';
import { toast } from 'sonner';
import { notifications, type PortalNotification } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';

const TYPE_COLORS: Record<string, { bg: string; dot: string }> = {
  appt_confirmed:    { bg: '#E1F5EE', dot: '#187f77' },
  appt_rescheduled:  { bg: '#FAEEDA', dot: '#BA7517' },
  appt_cancelled:    { bg: '#FAECE7', dot: '#D85A30' },
  order_confirmed:   { bg: '#EEF2FF', dot: '#534AB7' },
  order_ready:       { bg: '#E1F5EE', dot: '#187f77' },
  order_delivered:   { bg: '#F0FDF4', dot: '#639922' },
  appointment:       { bg: '#E1F5EE', dot: '#187f77' },
  health_reminder:   { bg: '#FEF3C7', dot: '#D97706' },
  default:           { bg: '#F9FAFB', dot: '#9CA3AF' },
};

export function NotificationBell() {
  const { customer } = useAuthStore();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const evtRef = useRef<EventSource | null>(null);

  const { data: countData } = useQuery({
    queryKey: ['notif-count'],
    queryFn: notifications.unreadCount,
    refetchInterval: 30 * 1000,
    enabled: !!customer,
  });

  const { data: notifList } = useQuery({
    queryKey: ['notif-list'],
    queryFn: () => notifications.list(),
    enabled: open,
    staleTime: 10 * 1000,
  });

  // SSE — reconectar si cae
  const connectSSE = useCallback(() => {
    if (!customer) return;
    if (evtRef.current) evtRef.current.close();
    const url = `/api/v1/portal/notifications/events`;
    const es = new EventSource(url, { withCredentials: true });
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'connected') return;
        qc.invalidateQueries({ queryKey: ['notif-count'] });
        qc.invalidateQueries({ queryKey: ['notif-list'] });
        toast(data.title, {
          description: data.body,
          duration: 5000,
          position: 'bottom-right',
        });
      } catch {}
    };
    es.onerror = () => {
      es.close();
      setTimeout(connectSSE, 5000);
    };
    evtRef.current = es;
  }, [customer, qc]);

  useEffect(() => {
    connectSSE();
    return () => evtRef.current?.close();
  }, [connectSSE]);

  async function markAll() {
    await notifications.markAllRead();
    qc.invalidateQueries({ queryKey: ['notif-count'] });
    qc.invalidateQueries({ queryKey: ['notif-list'] });
  }

  const unread = countData?.unread ?? 0;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative p-2 rounded-xl hover:bg-white/50 transition-colors"
      >
        <Bell className="h-5 w-5 text-foreground" />
        <AnimatePresence>
          {unread > 0 && (
            <motion.span
              key="badge"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
              className="absolute -top-0.5 -right-0.5 h-4.5 min-w-[18px] px-1 rounded-full text-white text-[10px] font-bold flex items-center justify-center"
              style={{ background: '#D85A30', fontSize: 10, lineHeight: '18px', height: 18 }}
            >
              {unread > 9 ? '9+' : unread}
            </motion.span>
          )}
        </AnimatePresence>
      </button>

      {/* Drawer */}
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40"
              onClick={() => setOpen(false)}
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 28, stiffness: 300 }}
              className="fixed top-0 right-0 bottom-0 z-50 w-full max-w-sm bg-white shadow-2xl flex flex-col"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-border">
                <div className="flex items-center gap-2">
                  <Bell className="h-5 w-5 text-foreground" />
                  <h2 className="font-display font-bold text-foreground">
                    Notificaciones
                  </h2>
                  {unread > 0 && (
                    <span className="text-[10px] font-bold bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                      {unread} nuevas
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {unread > 0 && (
                    <button
                      onClick={markAll}
                      className="text-xs text-primary-700 font-semibold flex items-center gap-1 hover:text-primary-800"
                    >
                      <Check className="h-3.5 w-3.5" />
                      Todas leídas
                    </button>
                  )}
                  <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-gray-100">
                    <X className="h-4 w-4 text-muted" />
                  </button>
                </div>
              </div>

              {/* Lista */}
              <div className="flex-1 overflow-y-auto divide-y divide-border">
                {!notifList || notifList.length === 0 ? (
                  <div className="flex flex-col items-center gap-3 py-16 text-center px-6">
                    <span className="text-4xl">🔔</span>
                    <p className="font-semibold text-foreground text-sm">Sin notificaciones</p>
                    <p className="text-muted text-xs">Aquí aparecerán actualizaciones de tus pedidos y citas.</p>
                  </div>
                ) : (
                  notifList.map((n) => (
                    <NotifItem key={n.id} notif={n} />
                  ))
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

function NotifItem({ notif }: { notif: PortalNotification }) {
  const colors = TYPE_COLORS[notif.type] ?? TYPE_COLORS.default;
  const isUnread = !notif.read_at;

  return (
    <div
      className="flex items-start gap-3.5 p-4 transition-colors"
      style={{ background: isUnread ? colors.bg : 'white' }}
    >
      <div
        className="h-2.5 w-2.5 rounded-full shrink-0 mt-1.5"
        style={{ background: isUnread ? colors.dot : '#E5E7EB' }}
      />
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-foreground text-sm leading-tight">{notif.title}</p>
        <p className="text-muted text-xs mt-0.5 leading-relaxed">{notif.body}</p>
        <p className="text-[10px] text-muted mt-1">
          {new Date(notif.created_at).toLocaleDateString('es-CO', {
            day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
          })}
        </p>
      </div>
    </div>
  );
}
