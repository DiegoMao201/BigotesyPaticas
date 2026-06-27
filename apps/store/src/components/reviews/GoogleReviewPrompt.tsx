'use client';

import { useEffect, useState } from 'react';
import { Star, X } from 'lucide-react';

const GOOGLE_REVIEW_URL = 'https://g.page/r/CfL67OgLB-10EBM/review';
const COOLDOWN_DAYS = 30;
const STORAGE_KEY = 'bp_google_review_prompted_at';
const MIN_VISITS = 3;
const VISITS_KEY = 'bp_visit_count';

function trackEvent(name: string, params?: Record<string, unknown>) {
  if (typeof window !== 'undefined') {
    window.gtag?.('event', name, params ?? {});
  }
}

export function GoogleReviewPrompt() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const visits = parseInt(localStorage.getItem(VISITS_KEY) ?? '0') + 1;
    localStorage.setItem(VISITS_KEY, String(visits));

    const lastPrompted = localStorage.getItem(STORAGE_KEY);
    if (lastPrompted) {
      const days = (Date.now() - parseInt(lastPrompted)) / (1000 * 60 * 60 * 24);
      if (days < COOLDOWN_DAYS) return;
    }

    if (visits < MIN_VISITS) return;

    const timer = setTimeout(() => setShow(true), 5000);
    return () => clearTimeout(timer);
  }, []);

  const handleAccept = () => {
    window.open(GOOGLE_REVIEW_URL, '_blank', 'noopener,noreferrer');
    localStorage.setItem(STORAGE_KEY, String(Date.now()));
    trackEvent('google_review_intent', { source: 'popup' });
    setShow(false);
  };

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_KEY, String(Date.now()));
    trackEvent('google_review_dismissed', { source: 'popup' });
    setShow(false);
  };

  if (!show) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
        onClick={handleDismiss}
      />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-2xl shadow-2xl p-8 max-w-md w-[90%] z-50 animate-in fade-in zoom-in-95">
        <button
          onClick={handleDismiss}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          <X size={20} />
        </button>

        <div className="text-center">
          <div className="flex justify-center gap-1 mb-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <Star key={i} className="w-10 h-10 fill-yellow-400 text-yellow-400" />
            ))}
          </div>

          <h3 className="text-2xl font-bold text-[#0d4a45] mb-2">
            ¿Te gusta Bigotes y Paticas? 🐾
          </h3>

          <p className="text-gray-600 mb-6">
            Una reseña honesta en Google nos ayuda muchísimo a llegar a más familias con mascotas
            en Pereira y Dosquebradas.
          </p>

          <button
            onClick={handleAccept}
            className="w-full bg-[#187f77] hover:bg-[#0d4a45] text-white font-semibold py-4 rounded-xl transition mb-3"
          >
            Dejar reseña en Google →
          </button>

          <button onClick={handleDismiss} className="w-full text-gray-500 hover:text-gray-700 py-2">
            Quizás después
          </button>

          <p className="text-xs text-gray-400 mt-4">
            Te toma 30 segundos · Cero spam · Suma 5 estrellas a Bigotes 🌟
          </p>
        </div>
      </div>
    </>
  );
}
