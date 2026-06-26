'use client';

import { useState } from 'react';
import type { Product } from '@/lib/api';

const TABS = ['Descripción', 'Detalles', 'Modo de uso', 'Reseñas', 'Envío'] as const;
type Tab = (typeof TABS)[number];

export function ProductTabs({ product }: { product: Product }) {
  const [active, setActive] = useState<Tab>('Descripción');
  const attrs = (product.attributes ?? {}) as Record<string, unknown>;
  const ai = product.enriched_content;

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

        {/* ── Descripción ── */}
        {active === 'Descripción' && (
          <div className="space-y-6">
            {/* Beneficios IA */}
            {ai?.beneficios && ai.beneficios.length > 0 && (
              <div className="grid sm:grid-cols-3 gap-3">
                {ai.beneficios.map((b, i) => (
                  <div key={i} className="flex items-start gap-2.5 p-4 rounded-2xl bg-teal-50 border border-teal-100">
                    <span className="text-teal-600 font-bold text-base flex-shrink-0">✓</span>
                    <span className="text-sm text-teal-800 leading-snug">
                      {b.replace(/^✓\s*/, '')}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Descripción IA o fallback del catálogo */}
            <div className="prose prose-sm max-w-none text-foreground">
              {ai?.descripcion ? (
                <p className="leading-relaxed whitespace-pre-line">{ai.descripcion}</p>
              ) : product.description ? (
                <p className="leading-relaxed whitespace-pre-line">{product.description}</p>
              ) : product.short_description ? (
                <p className="leading-relaxed">{product.short_description}</p>
              ) : (
                <p className="text-muted-foreground italic">
                  Descripción detallada disponible próximamente.
                </p>
              )}
            </div>

            {/* Recomendado para */}
            {ai?.recomendado_para && ai.recomendado_para.length > 0 && (
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">
                  Recomendado para
                </p>
                <div className="flex flex-wrap gap-2">
                  {ai.recomendado_para.map((r, i) => (
                    <span
                      key={i}
                      className="text-xs px-3 py-1.5 rounded-full bg-amber-50 border border-amber-100 text-amber-800 font-medium"
                    >
                      {r}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Advertencias */}
            {ai?.advertencias && ai.advertencias.length > 0 && (
              <div className="rounded-2xl bg-red-50 border border-red-100 p-4">
                <p className="text-xs font-bold uppercase tracking-widest text-red-600 mb-2">
                  Advertencias
                </p>
                <ul className="space-y-1">
                  {ai.advertencias.map((a, i) => (
                    <li key={i} className="text-sm text-red-700 flex items-start gap-1.5">
                      <span className="flex-shrink-0 mt-0.5">⚠️</span>
                      {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* ── Detalles ── */}
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
                {/* Detalles técnicos IA */}
                {ai?.detalles_tecnicos?.presentacion && (
                  <tr className="hover:bg-muted/30 transition-colors">
                    <td className="py-3 px-5 font-medium text-foreground">Presentación</td>
                    <td className="py-3 px-5 text-muted-foreground">{ai.detalles_tecnicos.presentacion}</td>
                  </tr>
                )}
                {ai?.detalles_tecnicos?.principio_activo && (
                  <tr className="hover:bg-muted/30 transition-colors">
                    <td className="py-3 px-5 font-medium text-foreground">Principio activo</td>
                    <td className="py-3 px-5 text-muted-foreground">{ai.detalles_tecnicos.principio_activo}</td>
                  </tr>
                )}
                {ai?.detalles_tecnicos?.ingredientes_principales && (
                  <tr className="hover:bg-muted/30 transition-colors">
                    <td className="py-3 px-5 font-medium text-foreground">Ingredientes</td>
                    <td className="py-3 px-5 text-muted-foreground">{ai.detalles_tecnicos.ingredientes_principales}</td>
                  </tr>
                )}
                {ai?.detalles_tecnicos?.edad_recomendada && (
                  <tr className="hover:bg-muted/30 transition-colors">
                    <td className="py-3 px-5 font-medium text-foreground">Edad</td>
                    <td className="py-3 px-5 text-muted-foreground capitalize">{ai.detalles_tecnicos.edad_recomendada}</td>
                  </tr>
                )}
                {ai?.detalles_tecnicos?.tamano_recomendado && (
                  <tr className="hover:bg-muted/30 transition-colors">
                    <td className="py-3 px-5 font-medium text-foreground">Tamaño</td>
                    <td className="py-3 px-5 text-muted-foreground capitalize">{ai.detalles_tecnicos.tamano_recomendado}</td>
                  </tr>
                )}
                {/* Atributos del catálogo (species, etc.) */}
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

        {/* ── Modo de uso ── */}
        {active === 'Modo de uso' && (
          <div className="space-y-4">
            {ai?.modo_de_uso ? (
              <p className="leading-relaxed text-muted-foreground whitespace-pre-line max-w-2xl">
                {ai.modo_de_uso}
              </p>
            ) : (attrs.uso || attrs.modo_de_uso) ? (
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

        {/* ── Reseñas ── */}
        {active === 'Reseñas' && (
          <div className="text-center py-10">
            <div className="text-5xl mb-4">⭐</div>
            <h3 className="font-display font-bold text-xl mb-2">Sin reseñas aún</h3>
            <p className="text-muted-foreground text-sm">
              Sé el primero en reseñar este producto para ayudar a otros dueños de mascotas.
            </p>
          </div>
        )}

        {/* ── Envío ── */}
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
