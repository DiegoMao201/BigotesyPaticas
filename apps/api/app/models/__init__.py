"""Re-exporta todos los modelos para que Alembic los detecte."""
from app.models.auth import PERMISSIONS, ROLE_DEFAULTS, Role, User, user_roles  # noqa
from app.models.catalog import Brand, Category, Product  # noqa
from app.models.common import Base  # noqa
from app.models.crm import Customer  # noqa
from app.models.finance import CashClosing  # noqa
from app.models.inventory import Stock, StockLocation, StockMovement  # noqa
from app.models.ops import AuditLog, LegacyIdMap  # noqa
from app.models.portal import (  # noqa
    Appointment, HealthRecord, LoyaltyPoint, Pet,
    PortalNotification, PortalOrder, PortalSession,
)
from app.models.purchasing import Purchase, PurchaseItem, Supplier, SupplierSkuMap  # noqa
from app.models.sales import Order, OrderItem, Payment  # noqa

__all__ = [
    "Base",
    "User", "Role", "user_roles", "PERMISSIONS", "ROLE_DEFAULTS",
    "Brand", "Category", "Product",
    "Customer",
    "StockLocation", "Stock", "StockMovement",
    "Order", "OrderItem", "Payment",
    "Purchase", "PurchaseItem",
    "Supplier", "SupplierSkuMap",
    "LegacyIdMap", "AuditLog",
    "CashClosing",
    "Pet", "HealthRecord", "Appointment", "PortalOrder",
    "PortalSession", "LoyaltyPoint", "PortalNotification",
]
