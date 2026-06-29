'use client';

import { useEffect, useState } from 'react';
import { Star, ExternalLink } from 'lucide-react';
import { trackEvent } from '@/lib/analytics';

interface GBPReview {
  reviewer_name: string;
  reviewer_photo: string | null;
  rating: number;
  comment: string | null;
  created_at: string;
}

interface GBPResponse {
  reviews: GBPReview[];
  aggregate: {
    avg: number;
    count: number;
  };
}

function StarRow({ rating, size = 'sm' }: { rating: number; size?: 'sm' | 'lg' }) {
  const cls = size === 'lg' ? 'w-6 h-6' : 'w-4 h-4';
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <Star key={s} className={`${cls} ${s <= rating ? 'fill-amber-400 text-amber-400' : 'text-gray-200'}`} />
      ))}
    </div>
  );
}

function ReviewCard({ review }: { review: GBPReview }) {
  const initials = review.reviewer_name
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();

  const date = new Date(review.created_at).toLocaleDateString('es-CO', {
    month: 'short',
    year: 'numeric',
  });

  return (
    <div className="rounded-3xl border border-border bg-card p-6 flex flex-col gap-4 h-full">
      <StarRow rating={review.rating} />
      {review.comment && (
        <p className="text-sm text-foreground leading-relaxed flex-1 line-clamp-4 italic">
          "{review.comment}"
        </p>
      )}
      <div className="flex items-center gap-3 pt-2 border-t border-border">
        {review.reviewer_photo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={review.reviewer_photo}
            alt={review.reviewer_name}
            className="w-9 h-9 rounded-full object-cover"
          />
        ) : (
          <div className="w-9 h-9 rounded-full gradient-brand flex items-center justify-center text-white text-xs font-bold shrink-0">
            {initials}
          </div>
        )}
        <div className="min-w-0">
          <p className="text-sm font-semibold truncate">{review.reviewer_name}</p>
          <p className="text-xs text-muted-foreground">{date} · Google</p>
        </div>
      </div>
    </div>
  );
}

export function RealReviewsSection() {
  const [data, setData] = useState<GBPResponse | null>(null);

  useEffect(() => {
    fetch('/api/v1/public/gbp-reviews?limit=6')
      .then((r) => r.json())
      .then(setData)
      .catch(() => null);
  }, []);

  if (!data || data.reviews.length === 0) return null;

  const { reviews, aggregate } = data;

  return (
    <section className="container-wide py-20">
      <div className="text-center mb-12">
        <p className="text-brand-600 font-semibold text-sm mb-2">Lo que dicen nuestros clientes</p>
        <h2 className="text-3xl md:text-4xl font-display font-extrabold mb-4">
          Reseñas reales en Google
        </h2>

        {/* Rating global */}
        {aggregate?.avg && (
          <div className="inline-flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-2xl px-6 py-3">
            <span className="text-4xl font-extrabold text-amber-600">{aggregate.avg.toFixed(1)}</span>
            <div className="text-left">
              <StarRow rating={Math.round(aggregate.avg)} size="lg" />
              <p className="text-xs text-amber-700 mt-1">{aggregate.count} reseñas verificadas en Google</p>
            </div>
            {/* Logo Google */}
            <svg className="w-8 h-8 ml-2 shrink-0" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
          </div>
        )}
      </div>

      {/* Grid de reseñas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {reviews.slice(0, 6).map((rev, i) => (
          <ReviewCard key={`${rev.reviewer_name}-${i}`} review={rev} />
        ))}
      </div>

      {/* CTA Google */}
      <div className="text-center mt-10">
        <a
          href="https://g.page/r/CfL67OgLB-10EBM/review"
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => trackEvent('gbp_click', { source: 'home_reviews_section' })}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-full border-2 border-brand-600 text-brand-600 font-semibold hover:bg-brand-600 hover:text-white transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
          Deja tu reseña en Google
        </a>
      </div>
    </section>
  );
}
