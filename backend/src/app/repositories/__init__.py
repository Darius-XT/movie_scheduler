"""仓储层统一导出。"""

from app.repositories.cinema import cinema_repository
from app.repositories.movie import movie_repository

__all__ = [
    "cinema_repository",
    "movie_repository",
]
