'use client';

import { useState } from 'react';
import type { Product } from '@/lib/api';

const TABS = ['Descripción', 'Detalles', 'Modo de uso', 'Reseñas', 'Envío'] as const;
type Tab = (typeof TABS)[number];

export function ProductTabs({ product }: { product: Product }) {
  const [active, setActive] = useState<Tab>('Descripción');
  const attrs = (product.attributes ?? {}) as Record<string, unknown>;

  return (
    <div>
      {/* Tab headers */}
      <div className="flex gap-0 border-b border-border overflow-x-auto scrollbar-none">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActive(tab)}
            className={`px-5 py-3.5 text-sm font-semibold whitespace-nowrap transition-all border-b-2 -mb-px ${
              active === tab
                ? 'border-brand-600 text-brand-600'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="py-8">
        {active === 'Descripción' && (
          <div className="prose prose-sm max-w-none text-foreground">
            {product.description ? (
              <p className="leading-relaxed whitespace-pre-line">{product.description}</p>
            ) : product.short_description ? (
              <p className="leading-relaxed">{product.short_description}</p>
            ) : (
              <p className="text-muted-foreground italic">
                Descripción detallada disponible próximamente.
              </p>
            )}
          </div>
        )}

        {active === 'Detalles' && (
          <div className="overflow-hidden rounded-2xl border border-border">
            <table className="min-w-full divide-y divide-border text-sm">
              <tbody className="divide-y divide-border">
                <tr className="hover:bg-muted/30 transition-colors">
                  <td className="py-3 px-5 font-medium text-foreground w-40">SKU</td>
                  <td className="py-3 px-5 text-muted-foreground font-mono">{product.sku}</td>
                </tr>
                {product.brand && (
                  <tr className="hover:bg-muted/30 transition-colors">
                    <td className="py-3 px-5 font-medium text-foreground">Marca</td>
                    <td className="py-3 px-5 text-muted-foreground">{product.brand.name}</td>
                  </tr>
                )}
                {product.category && (
                  <tr className="hover:bg-muted/30 transition-colors">
                    <td className="py-3 px-5 font-medium text-foreground">Categoría</td>
                    <td className="py-3 px-5 text-muted-foreground">{product.category.name}</td>
                  </tr>
                )}
                {Object.entries(attrs).map(([k, v]) => (
                  <tr key={k} className="hover:bg-muted/30 transition-colors">
                    <td className="py-3 px-5 font-medium text-foreground capitalize">
                      {k.replace(/_/g, ' ')}
                    </td>
                    <td className="py-3 px-5 text-muted-foreground capitalize">{String(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {active === 'Modo de uso' && (
          <div className="space-y-4">
            {(attrs.uso || attrs.modo_de_uso) ? (
              <p className="leading-relaxed text-muted-foreground whitespace-pre-line">
                {String(attrs.uso ?? attrs.modo_de_uso)}
              </p>
            ) : (
              <div className="rounded-2xl bg-amber-50 border border-amber-100 p-6 text-amber-800">
                <p className="font-semibold mb-1">Información no disponible</p>
                <p className="text-sm text-amber-700">
                  Las instrucciones de uso de este producto estarán disponibles próximamente.
                  ¿Tienes dudas? Escríbenos por WhatsApp.
                </p>
              </div>
            )}
          </div>
        )}

        {active === 'Reseñas' && (
          <div className="text-center py-10">
            <div className="text-5xl mb-4">⭐</div>
            <h3 className="font-display font-bold text-xl mb-2">Sin reseñas aún</h3>
            <p className="text-muted-foreground text-sm">
              Sé el primero en reseñar este producto para ayudar a otros dueños de mascotas.
            </p>
          </div>
        )}

        {active === 'Envío' && (
          <div className="space-y-4 max-w-lg">
            <div className="flex items-start gap-4 p-5 rounded-2xl bg-teal-50 border border-teal-100">
              <span className="text-2xl flex-shrink-0">🚚</span>
              <div>
                <p className="font-semibold text-teal-800">Envío a domicilio</p>
                <p className="text-sm text-teal-700 mt-1 leading-relaxed">
                  Entregas en 24 a 72 horas en Pereira y Dosquebradas, Risaralda.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4 p-5 rounded-2xl bg-amber-50 border border-amber-100">
              <span className="text-2xl flex-shrink-0">🎁</span>
              <div>
                <p className="font-semibold text-amber-800">Envío gratis</p>
                <p className="text-sm text-amber-700 mt-1 leading-relaxed">
                  En pedidos desde $30.000 dentro de nuestra zona de cobertura.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4 p-5 rounded-2xl bg-gray-50 border border-gray-200">
              <span className="text-2xl flex-shrink-0">📞</span>
              <div>
                <p className="font-semibold text-gray-800">Pedidos especiales</p>
                <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                  Para pedidos fuera de cobertura o al por mayor, contáctanos por WhatsApp.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
