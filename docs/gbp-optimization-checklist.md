# Google Business Profile — Checklist de Optimización

Última actualización: 2026-06-28 | Sprint 5

## Perfil base

- [ ] Nombre exacto: **Bigotes y Paticas**
- [ ] Categoría principal: **Pet store**
- [ ] Categorías secundarias: Pet supply store, Pet grooming service
- [ ] Descripción: usar el texto del `BUSINESS_INFO.description`
- [ ] Sitio web: `https://bigotesypaticas.com`
- [ ] Teléfono: +57 320 687 6633
- [ ] Dirección completa con código postal (Armenia, Risaralda)
- [ ] Horario actualizado (Lun-Sáb 8am-7pm, Dom 9am-5pm)

## Fotos (mínimo 10 fotos de alta calidad)

- [ ] Logo 1:1 (usar `icon-512.png`)
- [ ] Foto portada horizontal 16:9 (local, equipo, mascotas)
- [ ] Al menos 5 fotos de productos best-sellers
- [ ] Foto del interior / punto de venta si aplica
- [ ] Foto de entrega a domicilio (domiciliario + mascota)

## Posts (publicar mínimo 1 por semana)

- [ ] Oferta del mes (con botón "Comprar ahora")
- [ ] Tip de cuidado de mascotas (con enlace al blog)
- [ ] Recordatorio de entrega gratuita desde $30.000
- [ ] Destaque de reseña 5 estrellas reciente

## Reseñas

- [ ] Responder TODAS las reseñas (usar las plantillas de `whatsapp-templates.ts`)
- [ ] Nunca borrar ni reportar reseñas negativas sin responder primero
- [ ] Objetivo: mantener rating ≥ 4.7
- [ ] Template WhatsApp post-entrega: usar `delivered_with_review_cta`
- [ ] Script de sync automático: `scripts/sync_gbp_reviews.py` (cron diario 7am)

## Preguntas y respuestas

- [ ] ¿Hacen domicilio? → Sí, en Pereira y Dosquebradas zona urbana
- [ ] ¿Cuánto demora la entrega? → 24-72 horas hábiles
- [ ] ¿Tienen tienda física? → Punto de venta en Armenia, Risaralda
- [ ] ¿Aceptan tarjetas? → Sí, efectivo, tarjetas y transferencias
- [ ] ¿Tienen carnet veterinario? → Sí, digital gratuito en el portal

## Métricas a monitorear (mensual)

| Métrica | Objetivo |
|---------|----------|
| Calificación | ≥ 4.7 ⭐ |
| Reseñas totales | +10 por mes |
| Búsquedas directas | crecimiento mes a mes |
| Clics a sitio web | crecimiento mes a mes |
| Llamadas | crecimiento mes a mes |

## Automatizaciones implementadas (Sprint 5)

- `sync_gbp_reviews.py` — sync diario de reseñas GBP → BD
- `RealReviewsSection.tsx` — muestra reseñas reales en home de la tienda
- Template `delivered_with_review_cta` — WA post-entrega con CTA
- Admin panel `/reviews` — moderación y respuesta desde el admin
- Portal `/orders/[id]/calificar` — clientes califican desde el portal
