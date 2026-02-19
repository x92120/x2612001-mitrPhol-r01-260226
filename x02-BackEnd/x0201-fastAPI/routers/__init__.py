"""
Routers Package
===============
FastAPI routers for xMixing API.
"""

from .router_auth import router as auth_router
from .router_users import router as users_router
from .router_ingredients import router as ingredients_router
from .router_skus import router as skus_router
from .router_production import router as production_router
from .router_plants import router as plants_router
from .router_monitoring import router as monitoring_router
from .router_views import router as views_router
from .router_warehouses import router as warehouses_router

__all__ = [
    "auth_router",
    "users_router", 
    "ingredients_router",
    "skus_router",
    "production_router",
    "plants_router",
    "monitoring_router",
    "views_router",
    "warehouses_router"
]
