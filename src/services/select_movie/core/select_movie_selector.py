"""选择电影（喜爱电影）核心选择器"""

from typing import List, Optional
from src.db.db_connector import db_connector
from src.db.db_operator import DBOperator
from src.logger import logger
from datetime import datetime
import logging


class SelectMovieSelector:
    """喜爱电影选择器"""

    def __init__(self):
        pass

    def select_movies(
        self, filter_china_movies: bool = True, year_threshold: Optional[int] = None
    ) -> List[int]:
        logger.debug("开始筛选喜爱电影...")

        if year_threshold is None:
            year_threshold = datetime.now().year + 1

        try:
            with DBOperator(db_connector) as db_ops:
                all_movies = db_ops.get_all_movies()

                if not all_movies:
                    logger.warning("数据库中没有电影数据")
                    return []

                logger.debug(f"数据库中总共有 {len(all_movies)} 部电影")

                favorite_ids: List[int] = []
                for movie in all_movies:
                    movie_id = int(movie.id)  # type: ignore
                    if self._is_favorite_movie(
                        movie, filter_china_movies, year_threshold
                    ):
                        favorite_ids.append(movie_id)
                        logger.debug(f"选中喜爱电影: {movie.title} (ID: {movie_id})")

                logger.debug(f"筛选完成，共找到 {len(favorite_ids)} 部喜爱电影")
                logger.debug(
                    f"筛选条件: 过滤中国大陆电影={filter_china_movies}, 年份阈值={year_threshold}"
                )
                return favorite_ids

        except Exception as e:
            logger.error(f"筛选喜爱电影时发生异常: {e}")
            return []

    def _is_favorite_movie(
        self, movie, filter_china_movies: bool, year_threshold: int
    ) -> bool:
        if filter_china_movies:
            is_not_china = self._is_not_china_movie(movie)
        else:
            is_not_china = True

        is_before_threshold = self._is_before_year_threshold(movie, year_threshold)
        return is_not_china or is_before_threshold

    def _is_not_china_movie(self, movie) -> bool:
        if not movie.country:
            return False
        country = movie.country.strip()
        if "中国大陆" in country:
            return False
        return True

    def _is_before_year_threshold(self, movie, year_threshold: int) -> bool:
        if not movie.release_date:
            return False
        try:
            release_date = datetime.strptime(movie.release_date, "%Y-%m-%d")
            return release_date.year < year_threshold
        except (ValueError, TypeError):
            try:
                release_date = datetime.strptime(movie.release_date, "%Y-%m")
                return release_date.year < year_threshold
            except (ValueError, TypeError):
                try:
                    release_date = datetime.strptime(movie.release_date, "%Y")
                    return release_date.year < year_threshold
                except (ValueError, TypeError):
                    logger.debug(f"无法解析上映日期: {movie.release_date}")
                    return False


# 模块级实例
select_movie_selector = SelectMovieSelector()


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    favorite_ids = select_movie_selector.select_movies(
        filter_china_movies=True, year_threshold=2020
    )
    print(f"结果: 找到 {len(favorite_ids)} 部电影")
