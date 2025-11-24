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
        self, year_threshold: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """根据筛选条件选择喜爱的电影（返回完整电影信息字典列表）

        筛选规则：
        - 所有国外电影（非中国大陆）默认都会被选中
        - 中国大陆电影：只有当上映年份小于年份阈值时才会被选中

        Args:
            year_threshold (Optional[int]): 年份阈值，仅对中国大陆电影生效。
                如果为 None，则默认为当前年份+1（例如：2025年时默认为2026）。
                中国大陆电影的上映年份必须小于此阈值才会被选中。
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
                if self._is_favorite_movie(movie, year_threshold):
                    movie_dict = self._movie_to_dict(movie)
                    favorite_movies.append(movie_dict)
                    logger.debug(f"选中喜爱电影: {movie.title} (ID: {movie.id})")

            logger.debug(f"筛选完成，共找到 {len(favorite_movies)} 部喜爱电影")
            logger.debug(f"筛选条件: 年份阈值={year_threshold}（仅对中国大陆电影生效）")
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

    def _is_favorite_movie(self, movie, year_threshold: int) -> bool:
        """判断是否为喜爱的电影

        规则：
        - 国外电影（非中国大陆）：直接选中
        - 中国大陆电影：只有当上映年份小于阈值时才选中
        """
        is_china_movie = self._is_china_movie(movie)

        # 如果是国外电影，直接选中
        if not is_china_movie:
            return True

        # 如果是中国大陆电影，需要满足年份阈值
        return self._is_before_year_threshold(movie, year_threshold)

    def _is_china_movie(self, movie) -> bool:
        """判断是否为中国大陆电影"""
        if not movie.country:
            return False
        country = movie.country.strip()
        return "中国大陆" in country

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
    favorite_ids = movie_selector.select_movie(year_threshold=2020)
    print(f"结果: 找到 {len(favorite_ids)} 部电影")
