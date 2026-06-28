"""Router agregador V1."""
from fastapi import APIRouter

from app.api.v1 import (
    admin_etl,
    admin_portal,
    analytics,
    auth,
    blog,
    content,
    reviews,
    contact,
    customers,
    finance,
    health,
    intelligence,
    inventory,
    inventory_counts,
    landings,
    portal_appointments,
    portal_auth,
    portal_intelligence,
    portal_loyalty,
    portal_monitor,
    portal_notifications,
    portal_orders,
    portal_pets,
    portal_service_status,
    products,
    purchases,
    purchases_xml,
    sales,
    search,
    seo,
    suppliers,
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
# Legacy suppliers (lectura desde sheets ETL) → /v1/suppliers-legacy/...
api_router.include_router(finance.suppliers_router, prefix="/v1-legacy")
api_router.include_router(finance.closings_router, prefix="/v1")
api_router.include_router(suppliers.router, prefix="/v1")
api_router.include_router(purchases.router, prefix="/v1")
api_router.include_router(purchases_xml.router, prefix="/v1")
# Portal de fidelización — rutas bajo /v1/portal/...
api_router.include_router(portal_auth.router, prefix="/v1")
api_router.include_router(portal_pets.router, prefix="/v1")
api_router.include_router(portal_orders.router, prefix="/v1")
api_router.include_router(portal_appointments.router, prefix="/v1")
api_router.include_router(portal_loyalty.router, prefix="/v1")
api_router.include_router(portal_monitor.router, prefix="/v1")
api_router.include_router(portal_intelligence.router, prefix="/v1")
api_router.include_router(portal_notifications.router, prefix="/v1")
api_router.include_router(portal_notifications.admin_router, prefix="/v1")
api_router.include_router(portal_service_status.router, prefix="/v1")
api_router.include_router(admin_portal.router, prefix="/v1")
# Sprint 5: reseñas de productos + GBP sync
api_router.include_router(reviews.router)
api_router.include_router(reviews.admin_router)
api_router.include_router(reviews.public_router)
# Sprint 6A: content engine IA
api_router.include_router(content.router)
