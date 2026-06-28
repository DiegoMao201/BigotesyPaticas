'use client';

import { useEffect, useState } from 'react';
import { Star, ExternalLink } from 'lucide-react';
import { trackEvent } from '@/lib/analytics';

interface GBPReview {
  id: string;
  reviewer_name: string;
  reviewer_photo_url: string | null;
  rating: number;
  comment: string | null;
  created_at: string;
}

interface GBPSummary {
  overall_rating: number | null;
  total_reviews: number;
  reviews: GBPReview[];
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
        {review.reviewer_photo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={review.reviewer_photo_url}
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
  const [data, setData] = useState<GBPSummary | null>(null);

  useEffect(() => {
    fetch('/api/v1/public/gbp-reviews')
      .then((r) => r.json())
      .then(setData)
      .catch(() => null);
  }, []);

  if (!data || data.reviews.length === 0) return null;

  const { overall_rating, total_reviews, reviews } = data;

  return (
    <section className="container-wide py-20">
      <div className="text-center mb-12">
        <p className="text-brand-600 font-semibold text-sm mb-2">Lo que dicen nuestros clientes</p>
        <h2 className="text-3xl md:text-4xl font-display font-extrabold mb-4">
          Reseñas reales en Google
        </h2>

        {/* Rating global */}
        {overall_rating && (
          <div className="inline-flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-2xl px-6 py-3">
            <span className="text-4xl font-extrabold text-amber-600">{overall_rating.toFixed(1)}</span>
            <div className="text-left">
              <StarRow rating={Math.round(overall_rating)} size="lg" />
              <p className="text-xs text-amber-700 mt-1">{total_reviews} reseñas verificadas</p>
            </div>
          </div>
        )}
      </div>

      {/* Grid de reseñas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {reviews.slice(0, 6).map((rev) => (
          <ReviewCard key={rev.id} review={rev} />
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
