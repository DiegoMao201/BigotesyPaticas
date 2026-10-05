"""Router agregador V1."""

from fastapi import APIRouter

from app.api.v1 import (
    admin_etl,
    admin_partners,
    admin_portal,
    adoption,
    analytics,
    auth,
    blog,
    catalog_export,
    catalog_feed,
    community_public,
    contact,
    content,
    customers,
    finance,
    finance_export,
    health,
    intelligence,
    inventory,
    inventory_counts,
    landings,
    messenger,
    partner_admin,
    partner_auth,
    partners_public,
    portal_appointments,
    public_grooming,
    payment_links,
    payments,
    public_orders,
    portal_auth,
    portal_bookings,
    portal_intelligence,
    portal_location,
    portal_loyalty,
    portal_monitor,
    portal_notifications,
    portal_orders,
    portal_pets,
    portal_service_status,
    products,
    purchases,
    purchases_xml,
    purchases_inbox,
    rescues,
    reviews,
    sales,
    search,
    seo,
    sos,
    stories,
    suppliers,
    tiktok,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(blog.router, prefix="/v1")
api_router.include_router(search.router, prefix="/v1")
api_router.include_router(seo.router, prefix="/v1")
api_router.include_router(landings.router, prefix="/v1")
api_router.include_router(contact.router, prefix="/v1")
api_router.include_router(auth.router, prefix="/v1")
api_router.include_router(products.router, prefix="/v1")
api_router.include_router(products.brands_router, prefix="/v1")
api_router.include_router(products.categories_router, prefix="/v1")
api_router.include_router(products.admin_products_router, prefix="/v1")
api_router.include_router(inventory.router, prefix="/v1")
api_router.include_router(inventory_counts.router, prefix="/v1")
api_router.include_router(sales.router, prefix="/v1")
api_router.include_router(analytics.router, prefix="/v1")
api_router.include_router(intelligence.router, prefix="/v1")
api_router.include_router(customers.router, prefix="/v1")
api_router.include_router(admin_etl.router, prefix="/v1")
api_router.include_router(finance.router, prefix="/v1")
api_router.include_router(finance.expenses_router, prefix="/v1")
api_router.include_router(finance_export.export_router, prefix="/v1")
api_router.include_router(catalog_export.catalog_export_router, prefix="/v1")
# Legacy suppliers (lectura desde sheets ETL) → /v1/suppliers-legacy/...
api_router.include_router(finance.suppliers_router, prefix="/v1-legacy")
api_router.include_router(finance.closings_router, prefix="/v1")
api_router.include_router(suppliers.router, prefix="/v1")
# la bandeja va ANTES que purchases: si no, /purchases/inbox cae en /purchases/{id}
api_router.include_router(purchases_inbox.router, prefix="/v1")
api_router.include_router(purchases.router, prefix="/v1")
api_router.include_router(purchases_xml.router, prefix="/v1")
# Portal de fidelización — rutas bajo /v1/portal/...
api_router.include_router(portal_auth.router, prefix="/v1")
api_router.include_router(portal_pets.router, prefix="/v1")
api_router.include_router(portal_orders.router, prefix="/v1")
api_router.include_router(portal_appointments.router, prefix="/v1")
api_router.include_router(public_grooming.router, prefix="/v1")
# Pedido de la tienda web sin cuenta (2-oct-2026): entra al flujo del portal y se
# le cuenta a Google cuando el admin lo marca entregado.
api_router.include_router(public_orders.router, prefix="/v1")
# Pagos con Bold: el webhook y la consulta de estado sirven IGUAL a la tienda y al
# portal; el canal se distingue por el prefijo de la referencia (BPW- / BPP-).
api_router.include_router(payments.router, prefix="/v1")

# ALIAS BAJO /api/v1 — Y NO ES POR GUSTO.
# Esta API se sirve SIN el prefijo /api: /v1/... es la ruta real. El /api que se ve
# en el navegador lo pone el proxy de Next (apps/store/next.config.mjs reescribe
# /api/v1/* hacia la API), así que desde fuera parece que existe y no existe.
#
# El 5-oct-2026 el webhook se registró en el panel de Bold como
# https://api.bigotesypaticas.com/api/v1/webhooks/bold, con ese /api de más. En
# cualquier otro endpoint eso sería un 404 evidente; aquí sería invisible: Bold
# cobraría, reintentaría cinco veces contra una URL que no existe, y los pedidos se
# quedarían sin confirmar sin que nadie viera un error. Lo rescataría la
# conciliación, pero con minutos de retraso y por el camino de emergencia.
#
# Aceptar las dos rutas cuesta una línea y elimina de raíz una clase entera de
# fallo: la de la URL mal escrita en un panel que no es nuestro.
api_router.include_router(payments.router, prefix="/api/v1")
# Enlaces de cobro que crea el admin para ventas que no nacen en la web.
api_router.include_router(payment_links.router, prefix="/v1")
# Pago libre: el cliente arma su propio cobro, sin pedido detrás (abonos, saldos).
api_router.include_router(payment_links.publico, prefix="/v1")
api_router.include_router(portal_loyalty.router, prefix="/v1")
api_router.include_router(portal_monitor.router, prefix="/v1")
api_router.include_router(portal_intelligence.router, prefix="/v1")
api_router.include_router(portal_notifications.router, prefix="/v1")
api_router.include_router(portal_notifications.admin_router, prefix="/v1")
api_router.include_router(portal_service_status.router, prefix="/v1")
api_router.include_router(portal_location.router, prefix="/v1")
api_router.include_router(admin_portal.router, prefix="/v1")
# Fase 1 comunidad: SOS mascotas perdidas
# rescues.router (prefix /sos/rescues) DEBE registrarse antes que sos.router:
# sos.router define GET /sos/{sos_id} (path param genérico de un segmento),
# que si se registra primero intercepta GET /sos/rescues completo (Starlette
# matchea por orden de registro) — "rescues" se intenta parsear como UUID y
# revienta 422 en TODO el listado de animalitos encontrados.
api_router.include_router(rescues.router, prefix="/v1")
api_router.include_router(sos.router, prefix="/v1")
api_router.include_router(adoption.router, prefix="/v1")
api_router.include_router(community_public.router, prefix="/v1")
# Fase 3 comunidad: directorio de aliados/servicios + agenda real + panel de aliados
api_router.include_router(partners_public.router, prefix="/v1")
api_router.include_router(portal_bookings.router, prefix="/v1")
api_router.include_router(partner_auth.router, prefix="/v1")
api_router.include_router(partner_admin.router, prefix="/v1")
api_router.include_router(admin_partners.router, prefix="/v1")
# Sprint 5: reseñas de productos + GBP sync
api_router.include_router(reviews.router)
api_router.include_router(reviews.admin_router)
api_router.include_router(reviews.public_router)
# Sprint 6A: content engine IA
api_router.include_router(content.router)
# Sprint Stories: stories IA + manual
api_router.include_router(stories.router)
# TikTok Content Posting API — conexión OAuth + publicación de prueba
api_router.include_router(tiktok.router)
# Meta Catalog feed XML
api_router.include_router(catalog_feed.router)
# Messenger webhook
api_router.include_router(messenger.router)
