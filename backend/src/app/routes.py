"""统一注册所有领域的 router。"""

from __future__ import annotations

from fastapi import APIRouter

from app.city.endpoints import router as city_router
from app.movie.endpoints import router as movie_router
from app.planning.endpoints import router as planning_router
from app.show.endpoints import router as show_router
from app.update.endpoints import router as update_router

api_router = APIRouter(prefix="/api")
api_router.include_router(city_router)
api_router.include_router(movie_router)
api_router.include_router(planning_router)
api_router.include_router(show_router)
api_router.include_router(update_router)

__all__ = ["api_router"]
