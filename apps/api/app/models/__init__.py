"""Re-exporta todos los modelos para que Alembic los detecte."""

from app.models.auth import PERMISSIONS, ROLE_DEFAULTS, Role, User, user_roles
from app.models.catalog import Brand, Category, Product
from app.models.common import Base
from app.models.crm import Customer
from app.models.finance import CashClosing
from app.models.inventory import Stock, StockLocation, StockMovement
from app.models.ops import AuditLog, LegacyIdMap
from app.models.portal import (
    Appointment,
    HealthRecord,
    LoyaltyPoint,
    Pet,
    PortalNotification,
    PortalOrder,
    PortalSession,
)
from app.models.purchasing import Purchase, PurchaseItem, Supplier, SupplierSkuMap
from app.models.sales import Order, OrderItem, Payment

__all__ = [
    "Base",
    "User",
    "Role",
    "user_roles",
    "PERMISSIONS",
    "ROLE_DEFAULTS",
    "Brand",
    "Category",
    "Product",
    "Customer",
    "StockLocation",
    "Stock",
    "StockMovement",
    "Order",
    "OrderItem",
    "Payment",
    "Purchase",
    "PurchaseItem",
    "Supplier",
    "SupplierSkuMap",
    "LegacyIdMap",
    "AuditLog",
    "CashClosing",
    "Pet",
    "HealthRecord",
    "Appointment",
    "PortalOrder",
    "PortalSession",
    "LoyaltyPoint",
    "PortalNotification",
]
