"""业务服务层统一导出。"""

from app.services.city_service import city_service
from app.services.movie_service import movie_service
from app.services.show_service import show_service
from app.services.update_service import update_service

__all__ = [
    "city_service",
    "movie_service",
    "show_service",
    "update_service",
]
