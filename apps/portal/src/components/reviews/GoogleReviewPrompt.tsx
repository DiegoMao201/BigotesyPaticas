'use client';

import { useEffect, useState } from 'react';
import { Star, X, CheckCircle } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { orders } from '@/lib/api';

const GOOGLE_REVIEW_URL = 'https://g.page/r/CfL67OgLB-10EBM/review';
const COOLDOWN_DAYS = 30;
const STORAGE_KEY = 'bp_portal_review_prompted_at';
const MIN_DAYS_AFTER_ORDER = 7;
const API = '/api/v1';

export function GoogleReviewPrompt() {
  const [show, setShow] = useState(false);
  const [hovered, setHovered] = useState(0);
  const [selected, setSelected] = useState(0);
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const { data: orderList } = useQuery({
    queryKey: ['portal-orders-review-check'],
    queryFn: () => orders.list(1),
  });

  useEffect(() => {
    if (!orderList?.length) return;

    const lastPrompted = localStorage.getItem(STORAGE_KEY);
    if (lastPrompted) {
      const days = (Date.now() - parseInt(lastPrompted)) / (1000 * 60 * 60 * 24);
      if (days < COOLDOWN_DAYS) return;
    }

    const hasOldDeliveredOrder = orderList.some((o) => {
      if (o.status !== 'delivered') return false;
      const daysSince = (Date.now() - new Date(o.created_at).getTime()) / (1000 * 60 * 60 * 24);
      return daysSince >= MIN_DAYS_AFTER_ORDER;
    });
    if (!hasOldDeliveredOrder) return;

    const timer = setTimeout(() => setShow(true), 8000);
    return () => clearTimeout(timer);
  }, [orderList]);

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_KEY, String(Date.now()));
    setShow(false);
  };

  const handleSubmit = async () => {
    if (!selected) return;
    setLoading(true);

    // Save internally
    fetch(`${API}/contact/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stars: selected, comment: comment || null, source: 'portal' }),
    }).catch(() => {/* no-op */});

    setSubmitted(true);
    setLoading(false);
    localStorage.setItem(STORAGE_KEY, String(Date.now()));
    // NO usar window.open() automático: los navegadores móviles lo bloquean
    // si no es disparado directamente por el usuario. El botón en success
    // es un <a target="_blank"> que el usuario toca voluntariamente.
  };

  if (!show) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/60 z-50" onClick={handleDismiss} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-3xl shadow-2xl p-7 max-w-sm w-[90%] z-50">
        <button onClick={handleDismiss} className="absolute top-4 right-4 text-gray-400">
          <X size={20} />
        </button>

        {submitted ? (
          <div className="text-center py-4">
            <CheckCircle className="h-12 w-12 text-teal-500 mx-auto mb-3" />
            <h3 className="text-xl font-bold text-teal-800 mb-2">¡Gracias! 🐾</h3>
            <p className="text-gray-600 text-sm mb-5">
              {selected >= 4
                ? '¿Nos ayudas también en Google? Solo toma 30 segundos.'
                : 'Recibimos tu calificación. ¡Vamos a mejorar!'}
            </p>

            {selected >= 4 && (
              <a
                href={GOOGLE_REVIEW_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 w-full bg-teal-600 hover:bg-teal-700 text-white font-bold py-3 rounded-2xl transition mb-3"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Dejar reseña en Google →
              </a>
            )}

            <button
              onClick={() => setShow(false)}
              className="w-full text-gray-400 text-sm py-2"
            >
              {selected >= 4 ? 'Ahora no' : 'Cerrar'}
            </button>
          </div>
        ) : (
          <div className="text-center">
            <h3 className="text-xl font-bold text-teal-800 mb-1">
              ¿Cómo fue tu pedido? 🐾
            </h3>
            <p className="text-gray-500 text-sm mb-5">
              Solo toma 10 segundos
            </p>

            {/* Stars */}
            <div className="flex justify-center gap-2 mb-4">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  onMouseEnter={() => setHovered(n)}
                  onMouseLeave={() => setHovered(0)}
                  onClick={() => setSelected(n)}
                  className="transition-transform hover:scale-110 active:scale-95"
                >
                  <Star
                    className={`w-11 h-11 transition-colors ${
                      n <= (hovered || selected)
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'fill-gray-200 text-gray-200'
                    }`}
                  />
                </button>
              ))}
            </div>

            {selected > 0 && (
              <p className="text-sm font-medium text-gray-600 mb-3">
                {selected === 1 && 'Muy malo 😟'}
                {selected === 2 && 'Regular 😐'}
                {selected === 3 && 'Bueno 🙂'}
                {selected === 4 && 'Muy bueno 😊'}
                {selected === 5 && '¡Excelente! 🤩'}
              </p>
            )}

            {selected > 0 && selected <= 3 && (
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="¿Qué podemos mejorar? (opcional)"
                rows={2}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-teal-500 resize-none"
              />
            )}

            <button
              onClick={handleSubmit}
              disabled={!selected || loading}
              className="w-full bg-teal-600 hover:bg-teal-700 disabled:bg-gray-200 disabled:text-gray-400 text-white font-bold py-3 rounded-2xl transition mb-2"
            >
              {loading ? 'Enviando...' : selected ? `Calificar ${selected} ⭐` : 'Selecciona estrellas'}
            </button>

            {selected >= 4 && (
              <p className="text-xs text-gray-400">
                Al calificar se abrirá Google en una pestaña nueva.
              </p>
            )}

            <button onClick={handleDismiss} className="w-full text-gray-400 text-sm py-2">
              Ahora no
            </button>
          </div>
        )}
      </div>
    </>
  );
}
