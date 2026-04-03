"""场次抓取用例依赖的外部访问封装，提供流程需要的数据访问能力。"""

from __future__ import annotations

from typing import cast

from app.core.exceptions import DataParsingError, ExternalDependencyError
from app.repositories.movie_repository import movie_repository
from app.use_cases.show_fetching.models import FetchedShowItem
from app.use_cases.show_fetching.parsers.cinema_parser import cinema_parser
from app.use_cases.show_fetching.parsers.cinema_show_parser import cinema_show_parser
from app.use_cases.show_fetching.parsers.show_date_parser import show_date_parser
from app.use_cases.show_fetching.scrapers.cinema_scraper import cinema_scraper
from app.use_cases.show_fetching.scrapers.cinema_show_scraper import cinema_show_scraper
from app.use_cases.show_fetching.scrapers.show_date_scraper import show_date_scraper


class ShowFetchingGateway:
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
        success, json_content = show_date_scraper.scrape_showdate(movie_id, city_id)
        if not success or not json_content:
            raise ExternalDependencyError(f"获取电影 {movie_id} 在城市 {city_id} 的排片日期失败")

        show_dates = show_date_parser.parse_showdate(json_content)
        if not show_dates:
            raise DataParsingError(f"电影 {movie_id} 在城市 {city_id} 的排片日期解析结果为空")

        return show_dates

    def get_cinemas(self, movie_id: int, show_date: str, city_id: int) -> list[int]:
        """抓取指定电影在某日的全部影院 ID。"""
        all_cinema_ids: list[int] = []
        limit = 20
        offset = 0

        while True:
            success, json_content = cinema_scraper.scrape_cinemas(
                movie_id,
                show_date,
                city_id,
                limit,
                offset,
            )
            if not success or not json_content:
                raise ExternalDependencyError(
                    f"获取影院信息失败，movie_id={movie_id}, city_id={city_id}, show_date={show_date}, offset={offset}"
                )

            cinema_ids, is_last_page = cinema_parser.parse_cinemas(json_content)
            if not cinema_ids and not is_last_page:
                raise DataParsingError(
                    f"影院分页解析结果为空，movie_id={movie_id}, city_id={city_id}, show_date={show_date}, offset={offset}"
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
        success, json_content = cinema_show_scraper.scrape_cinema_shows(cinema_id, city_id)
        if not success or not json_content:
            raise ExternalDependencyError(f"获取影院 {cinema_id} 在城市 {city_id} 的场次信息失败")

        show_items = cinema_show_parser.parse_cinema_shows(json_content, movie_name, show_date)
        if not show_items:
            raise DataParsingError(
                f"影院 {cinema_id} 在城市 {city_id} 的场次信息解析结果为空，show_date={show_date}"
            )

        return show_items


show_fetching_gateway = ShowFetchingGateway()
