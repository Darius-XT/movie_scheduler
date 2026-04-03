"""V1 路由聚合器。"""

from fastapi import APIRouter

from app.api.v1.endpoints.city_endpoint import router as city_router
from app.api.v1.endpoints.movie_endpoint import router as movie_router
from app.api.v1.endpoints.show_endpoint import router as show_router
from app.api.v1.endpoints.update_endpoint import router as update_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(city_router)
api_router.include_router(update_router)
api_router.include_router(movie_router)
api_router.include_router(show_router)
