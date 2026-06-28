'use client';

import { useState, useEffect } from 'react';
import { Star, ThumbsUp } from 'lucide-react';
import { trackEvent } from '@/lib/analytics';

interface Review {
  id: string;
  rating: number;
  title: string | null;
  comment: string | null;
  reviewer_name: string;
  pet_name: string | null;
  photo_urls: string[];
  helpful_count: number;
  created_at: string;
}

interface ReviewsData {
  reviews: Review[];
  total: number;
  avg_rating: number | null;
  count: number;
}

function Stars({ rating }: { rating: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <Star key={s} className={`w-4 h-4 ${s <= rating ? 'fill-amber-400 text-amber-400' : 'text-gray-200'}`} />
      ))}
    </div>
  );
}

function RatingBar({ label, count, total }: { label: string; count: number; total: number }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="w-14 text-right text-muted-foreground text-xs">{label}</span>
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-full bg-amber-400 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-xs text-muted-foreground">{count}</span>
    </div>
  );
}

export function ProductReviews({
  productId,
  initialRatingAvg,
  initialRatingCount,
}: {
  productId: string;
  initialRatingAvg: number | null;
  initialRatingCount: number;
}) {
  const [data, setData] = useState<ReviewsData | null>(null);
  const [page, setPage] = useState(1);
  const [voted, setVoted] = useState<Record<string, boolean>>({});

  useEffect(() => {
    fetch(`/api/v1/products/${productId}/reviews?page=${page}&page_size=5`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => null);
  }, [productId, page]);

  async function voteHelpful(reviewId: string) {
    if (voted[reviewId]) return;
    await fetch(`/api/v1/products/${productId}/reviews/${reviewId}/helpful`, { method: 'POST' });
    setVoted((v) => ({ ...v, [reviewId]: true }));
    setData((d) =>
      d
        ? {
            ...d,
            reviews: d.reviews.map((r) =>
              r.id === reviewId ? { ...r, helpful_count: r.helpful_count + 1 } : r
            ),
          }
        : d
    );
    trackEvent('review_helpful', { product_id: productId, review_id: reviewId });
  }

  if (initialRatingCount === 0 && !data?.count) return null;

  const distribution = (data as ReviewsData & { distribution?: Record<string, number> })?.distribution ?? {};
  const totalCount = data?.count ?? initialRatingCount;
  const avgRating = data?.avg_rating ?? initialRatingAvg;

  return (
    <section className="py-12">
      <h2 className="text-2xl font-display font-bold mb-8">
        Reseñas de clientes{totalCount > 0 ? ` (${totalCount})` : ''}
      </h2>

      {/* Resumen */}
      {avgRating != null && totalCount > 0 && (
        <div className="flex flex-col sm:flex-row gap-8 mb-10 p-6 rounded-2xl bg-amber-50 border border-amber-100">
          <div className="text-center shrink-0">
            <p className="text-5xl font-extrabold text-amber-600">{avgRating.toFixed(1)}</p>
            <div className="flex justify-center mt-2">
              <Stars rating={Math.round(avgRating)} />
            </div>
            <p className="text-xs text-muted-foreground mt-1">{totalCount} reseñas</p>
          </div>
          {Object.keys(distribution).length > 0 && (
            <div className="flex-1 space-y-1.5">
              {[5, 4, 3, 2, 1].map((star) => (
                <RatingBar
                  key={star}
                  label={`${star} ⭐`}
                  count={distribution[String(star)] ?? 0}
                  total={totalCount}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Lista */}
      {data?.reviews && data.reviews.length > 0 ? (
        <div className="space-y-6">
          {data.reviews.map((rev) => {
            const date = new Date(rev.created_at).toLocaleDateString('es-CO', { month: 'long', year: 'numeric' });
            return (
              <div key={rev.id} className="rounded-2xl border border-border p-5 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <Stars rating={rev.rating} />
                    {rev.title && <p className="font-semibold mt-1">{rev.title}</p>}
                  </div>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">{date}</span>
                </div>
                {rev.comment && (
                  <p className="text-sm text-foreground leading-relaxed">{rev.comment}</p>
                )}
                {rev.photo_urls.length > 0 && (
                  <div className="flex gap-2">
                    {rev.photo_urls.map((url, i) => (
                      <a key={i} href={url} target="_blank" rel="noopener noreferrer">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={url} alt="" className="w-16 h-16 rounded-xl object-cover border border-border" />
                      </a>
                    ))}
                  </div>
                )}
                <div className="flex items-center justify-between pt-1">
                  <div className="text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">{rev.reviewer_name}</span>
                    {rev.pet_name && <span> · mascota: {rev.pet_name}</span>}
                  </div>
                  <button
                    onClick={() => voteHelpful(rev.id)}
                    disabled={voted[rev.id]}
                    className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-brand-600 transition-colors disabled:opacity-50"
                  >
                    <ThumbsUp className="w-3.5 h-3.5" />
                    Útil ({rev.helpful_count})
                  </button>
                </div>
              </div>
            );
          })}

          {/* Paginación */}
          {data.total > 5 && (
            <div className="flex justify-center gap-3 pt-4">
              <button
                onClick={() => setPage((p) => p - 1)}
                disabled={page <= 1}
                className="px-4 py-2 rounded-xl border border-border text-sm hover:bg-accent disabled:opacity-40 transition-colors"
              >
                Anterior
              </button>
              <span className="flex items-center text-sm text-muted-foreground px-2">
                Pág {page}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page * 5 >= data.total}
                className="px-4 py-2 rounded-xl border border-border text-sm hover:bg-accent disabled:opacity-40 transition-colors"
              >
                Siguiente
              </button>
            </div>
          )}
        </div>
      ) : (
        <p className="text-muted-foreground text-sm">Aún no hay reseñas aprobadas para este producto.</p>
      )}
    </section>
  );
}
