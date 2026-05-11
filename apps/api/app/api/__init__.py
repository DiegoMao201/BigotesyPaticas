"""Router agregador V1."""
from fastapi import APIRouter

from app.api.v1 import admin_etl, analytics, auth, customers, health, inventory, products, sales

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/v1")
api_router.include_router(products.router, prefix="/v1")
api_router.include_router(products.brands_router, prefix="/v1")
api_router.include_router(products.categories_router, prefix="/v1")
api_router.include_router(inventory.router, prefix="/v1")
api_router.include_router(sales.router, prefix="/v1")
api_router.include_router(analytics.router, prefix="/v1")
api_router.include_router(customers.router, prefix="/v1")
api_router.include_router(admin_etl.router, prefix="/v1")
