'use client';

import { useEffect, useState } from 'react';
import { Star, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { orders } from '@/lib/api';

const GOOGLE_REVIEW_URL = 'https://g.page/r/CfL67OgLB-10EBM/review';
const COOLDOWN_DAYS = 30;
const STORAGE_KEY = 'bp_portal_review_prompted_at';
const MIN_DAYS_AFTER_ORDER = 7;

export function GoogleReviewPrompt() {
  const [show, setShow] = useState(false);

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

    // Find a delivered order older than 7 days
    const hasOldDeliveredOrder = orderList.some((o) => {
      if (o.status !== 'delivered') return false;
      const orderDate = new Date(o.created_at).getTime();
      const daysSince = (Date.now() - orderDate) / (1000 * 60 * 60 * 24);
      return daysSince >= MIN_DAYS_AFTER_ORDER;
    });

    if (!hasOldDeliveredOrder) return;

    const timer = setTimeout(() => setShow(true), 8000);
    return () => clearTimeout(timer);
  }, [orderList]);

  const handleAccept = () => {
    window.open(GOOGLE_REVIEW_URL, '_blank', 'noopener,noreferrer');
    localStorage.setItem(STORAGE_KEY, String(Date.now()));
    setShow(false);
  };

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_KEY, String(Date.now()));
    setShow(false);
  };

  if (!show) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/60 z-50" onClick={handleDismiss} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-3xl shadow-2xl p-8 max-w-sm w-[90%] z-50">
        <button onClick={handleDismiss} className="absolute top-4 right-4 text-gray-400">
          <X size={20} />
        </button>
        <div className="text-center">
          <div className="flex justify-center gap-1 mb-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Star key={i} className="w-8 h-8 fill-yellow-400 text-yellow-400" />
            ))}
          </div>
          <h3 className="text-xl font-bold text-teal-800 mb-2">
            ¿Cómo fue tu experiencia? 🐾
          </h3>
          <p className="text-gray-600 text-sm mb-5">
            Tu opinión en Google ayuda a más familias a encontrarnos. ¡Solo toma 30 segundos!
          </p>
          <button
            onClick={handleAccept}
            className="w-full bg-teal-600 hover:bg-teal-700 text-white font-bold py-3 rounded-2xl transition mb-2"
          >
            Dejar reseña en Google →
          </button>
          <button onClick={handleDismiss} className="w-full text-gray-400 text-sm py-2">
            Quizás después
          </button>
        </div>
      </div>
    </>
  );
}
