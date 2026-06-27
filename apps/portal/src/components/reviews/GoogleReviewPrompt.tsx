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

    // Open Google in new tab for 4-5 star ratings
    if (selected >= 4) {
      setTimeout(() => {
        window.open(GOOGLE_REVIEW_URL, '_blank', 'noopener,noreferrer');
      }, 800);
    }
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
            <h3 className="text-xl font-bold text-teal-800 mb-2">
              ¡Gracias! 🐾
            </h3>
            <p className="text-gray-600 text-sm">
              {selected >= 4
                ? 'Tu reseña de Google se abrió en una nueva pestaña.'
                : 'Recibimos tu calificación. ¡Vamos a mejorar!'}
            </p>
            <button
              onClick={() => setShow(false)}
              className="mt-5 px-6 py-2 rounded-2xl bg-teal-600 text-white font-semibold text-sm"
            >
              Cerrar
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
