import { ImageResponse } from 'next/og';
import type { NextRequest } from 'next/server';

export const runtime = 'edge';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const product = searchParams.get('product') || 'Bigotes y Paticas';
  const price = searchParams.get('price') || '';
  const category = searchParams.get('category') || '';

  return new ImageResponse(
    (
      <div
        style={{
          background: 'linear-gradient(135deg, #187f77 0%, #0d4a45 100%)',
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 72,
          color: 'white',
          fontFamily: 'sans-serif',
        }}
      >
        {/* Marca */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 48 }}>
          <div
            style={{
              fontSize: 64,
              background: 'rgba(255,255,255,0.15)',
              borderRadius: 16,
              width: 80,
              height: 80,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            🐾
          </div>
          <div style={{ fontSize: 36, fontWeight: 700, opacity: 0.9 }}>
            Bigotes y Paticas
          </div>
        </div>

        {/* Producto */}
        <div
          style={{
            fontSize: product.length > 40 ? 44 : 56,
            fontWeight: 800,
            textAlign: 'center',
            lineHeight: 1.2,
            maxWidth: 900,
          }}
        >
          {product}
        </div>

        {category && (
          <div
            style={{
              marginTop: 24,
              fontSize: 28,
              opacity: 0.75,
              background: 'rgba(255,255,255,0.12)',
              borderRadius: 50,
              padding: '8px 28px',
            }}
          >
            {category}
          </div>
        )}

        {price && (
          <div style={{ fontSize: 52, fontWeight: 800, color: '#f5a641', marginTop: 36 }}>
            ${Number(price).toLocaleString('es-CO')}
          </div>
        )}

        {/* Footer */}
        <div
          style={{
            position: 'absolute',
            bottom: 48,
            fontSize: 24,
            opacity: 0.65,
            display: 'flex',
            alignItems: 'center',
            gap: 24,
          }}
        >
          <span>📦 Envío 24-72h</span>
          <span>·</span>
          <span>📍 Pereira y Dosquebradas</span>
          <span>·</span>
          <span>bigotesypaticas.com</span>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    },
  );
}
