"""路由层统一导出。"""

from fastapi import APIRouter

from app.api.endpoints.city import router as city_router
from app.api.endpoints.movie import router as movie_router
from app.api.endpoints.show import router as show_router
from app.api.endpoints.update import router as update_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(city_router)
api_router.include_router(update_router)
api_router.include_router(movie_router)
api_router.include_router(show_router)

__all__ = ["api_router"]
