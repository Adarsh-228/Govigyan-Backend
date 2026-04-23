from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.db import router as db_router
from app.api.routes.health import router as health_router
from app.api.routes.inventory import router as inventory_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(db_router)
api_router.include_router(inventory_router)
