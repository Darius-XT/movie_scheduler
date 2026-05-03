"""场次抓取用例依赖的外部访问封装。"""

from __future__ import annotations

from typing import cast

from app.repositories.movie import movie_repository
from app.show.cinema_client import cinema_client
from app.show.date_client import date_client
from app.show.entities import FetchedShowItem
from app.show.show_client import show_client


class ShowGateway:
    """封装场次用例所需的数据查询与抓取能力。"""

    def get_movie_name(self, movie_id: int) -> str | None:
        """从数据库读取电影名称。"""
        movie = movie_repository.get_movie_by_id(movie_id)
        if movie is None:
            return None

        movie_title = cast(str | None, getattr(movie, "title", None))
        if movie_title is None:
            return None

        return movie_title

    def get_show_dates(self, movie_id: int, city_id: int) -> list[str]:
        """抓取电影可排片日期。"""
        return date_client.get_show_dates(movie_id, city_id)

    def get_cinemas(self, movie_id: int, show_date: str, city_id: int) -> list[int]:
        """抓取指定电影在某日的全部影院 ID。"""
        all_cinema_ids: list[int] = []
        limit = 20
        offset = 0

        while True:
            cinema_ids, is_last_page = cinema_client.get_cinema_ids(
                movie_id,
                show_date,
                city_id,
                limit,
                offset,
            )

            all_cinema_ids.extend(cinema_ids)
            if is_last_page:
                return all_cinema_ids

            offset += limit

    def get_cinema_shows(
        self,
        cinema_id: int,
        movie_name: str,
        city_id: int,
        show_date: str | None = None,
    ) -> list[FetchedShowItem]:
        """抓取指定影院中某部电影的场次，可选限制到指定日期。"""
        return show_client.get_cinema_shows(cinema_id, city_id, movie_name, show_date)


show_gateway = ShowGateway()
