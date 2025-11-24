"""选择电影（喜爱电影）核心选择器"""

from typing import List, Optional, Dict, Any
from src.db.db_operate_manager import db_operate_manager
from src.utils.logger import logger
from datetime import datetime
import logging


class MovieSelector:
    """喜爱电影选择器"""

    def __init__(self):
        pass

    def select_movie(
        self, filter_china_movies: bool = True, year_threshold: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """根据筛选条件选择喜爱的电影（返回完整电影信息字典列表）

        Args:
            filter_china_movies (bool): 是否过滤掉中国大陆电影。
                默认为 True（过滤掉中国大陆电影）。
                如果为 True，则排除制片国家包含"中国大陆"的电影。
                如果为 False，则不进行国家过滤。
                示例值: True, False
            year_threshold (Optional[int]): 年份阈值。
                如果为 None，则默认为当前年份+1（例如：2025年时默认为2026）。
                如果电影的上映年份小于此阈值，即使是中国大陆电影也会被选中。
                示例值: None, 2020, 2025

        Returns:
            List[Dict[str, Any]]: 符合条件的电影完整信息字典列表（来自数据库）。
                如果未找到符合条件的电影，返回空列表 []。
                列表中每个元素包含电影的各个字段（id, title, score, genres, actors, release_year, is_showing,
                director, country, language, duration, description）。
        """
        logger.debug("开始筛选喜爱电影...")

        if year_threshold is None:
            year_threshold = datetime.now().year + 1

        try:
            all_movies = db_operate_manager.get_all_movies()

            if not all_movies:
                logger.warning("数据库中没有电影数据")
                return []

            logger.debug(f"数据库中总共有 {len(all_movies)} 部电影")

            favorite_movies: List[Dict[str, Any]] = []
            for movie in all_movies:
                if self._is_favorite_movie(movie, filter_china_movies, year_threshold):
                    movie_dict = self._movie_to_dict(movie)
                    favorite_movies.append(movie_dict)
                    logger.debug(f"选中喜爱电影: {movie.title} (ID: {movie.id})")

            logger.debug(f"筛选完成，共找到 {len(favorite_movies)} 部喜爱电影")
            logger.debug(
                f"筛选条件: 过滤中国大陆电影={filter_china_movies}, 年份阈值={year_threshold}"
            )
            return favorite_movies

        except Exception as e:
            logger.error(f"筛选喜爱电影时发生异常: {e}")
            return []

    def _movie_to_dict(self, movie) -> Dict[str, Any]:
        """将数据库中的 Movie 实例转换为字典"""
        return {
            "id": int(movie.id) if getattr(movie, "id", None) is not None else None,
            "title": getattr(movie, "title", None),
            "score": getattr(movie, "score", None),
            "genres": getattr(movie, "genres", None),
            "actors": getattr(movie, "actors", None),
            "release_year": getattr(movie, "release_year", None),
            "is_showing": getattr(movie, "is_showing", False),
            "director": getattr(movie, "director", None),
            "country": getattr(movie, "country", None),
            "language": getattr(movie, "language", None),
            "duration": getattr(movie, "duration", None),
            "description": getattr(movie, "description", None),
        }

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
        if not movie.release_year:
            return False
        try:
            release_year = int(movie.release_year)
            return release_year < year_threshold
        except (ValueError, TypeError):
            logger.debug(f"无法解析上映年份: {movie.release_year}")
            return False


# 模块级实例
movie_selector = MovieSelector()


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    favorite_ids = movie_selector.select_movie(
        filter_china_movies=True, year_threshold=2020
    )
    print(f"结果: 找到 {len(favorite_ids)} 部电影")
