"""电影筛选用例依赖的数据访问封装。"""

from __future__ import annotations

from app.models.movie import Movie
from app.repositories.movie import movie_repository


class MovieGateway:
    """封装电影筛选用例需要的电影数据读取能力。"""

    def get_all_movies(self) -> list[Movie]:
        """读取全部电影记录。"""
        return movie_repository.get_all_movies()


movie_gateway = MovieGateway()
