# 对数据库中更新后的电影进行筛选, 可以选择是否过滤中国大陆电影, 以及仅选择 xx 年之前的电影

from typing import List, Optional
from src.db.db_connector import db_connector
from src.db.db_operator import DBOperator
from src.logger import logger
from datetime import datetime
import logging


class FavoriteMovieSelector:
    """喜爱电影选择器类"""

    def __init__(self):
        """初始化筛选器"""
        pass

    # 将所有符合筛选条件的电影 id 以列表形式返回
    def select_favorite_movies(
        self, filter_china_movies: bool = True, year_threshold: Optional[int] = None
    ) -> List[int]:
        logger.debug("开始筛选喜爱电影...")

        # 设置年份阈值
        if year_threshold is None:
            year_threshold = datetime.now().year + 1

        try:
            with DBOperator(db_connector) as db_ops:
                # 获取所有电影
                all_movies = db_ops.get_all_movies()

                if not all_movies:
                    logger.warning("数据库中没有电影数据")
                    return []

                logger.debug(f"数据库中总共有 {len(all_movies)} 部电影")

                favorite_ids = []

                for movie in all_movies:
                    movie_id = int(movie.id)  # type: ignore

                    # 检查是否符合喜爱条件
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

    # 判断单部电影是否为喜爱电影
    def _is_favorite_movie(
        self, movie, filter_china_movies: bool, year_threshold: int
    ) -> bool:
        # 条件1: 如果启用过滤中国大陆电影，则检查国家
        if filter_china_movies:
            is_not_china = self._is_not_china_movie(movie)
        else:
            is_not_china = True  # 不过滤中国大陆电影时，此条件总是满足

        # 条件2: 检查上映时间是否早于阈值年份
        is_before_threshold = self._is_before_year_threshold(movie, year_threshold)

        # 满足任一条件即为喜爱电影
        return is_not_china or is_before_threshold

    # 判断单部电影是否为非中国大陆电影
    def _is_not_china_movie(self, movie) -> bool:
        if not movie.country:
            return False

        country = movie.country.strip()

        # 检查是否包含中国大陆关键词:
        if "中国大陆" in country:
            return False

        return True

    # 判断单部电影是否早于阈值年份
    def _is_before_year_threshold(self, movie, year_threshold: int) -> bool:
        if not movie.release_date:
            return False

        try:
            # 解析上映日期
            release_date = datetime.strptime(movie.release_date, "%Y-%m-%d")
            return release_date.year < year_threshold
        except (ValueError, TypeError):
            # 如果日期格式不正确，尝试其他格式
            try:
                # 尝试 YYYY-MM 格式
                release_date = datetime.strptime(movie.release_date, "%Y-%m")
                return release_date.year < year_threshold
            except (ValueError, TypeError):
                # 尝试 YYYY 格式
                try:
                    release_date = datetime.strptime(movie.release_date, "%Y")
                    return release_date.year < year_threshold
                except (ValueError, TypeError):
                    logger.debug(f"无法解析上映日期: {movie.release_date}")
                    return False


# 创建全局实例（使用默认配置）
favorite_movies_selector = FavoriteMovieSelector()


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)

    favorite_ids = favorite_movies_selector.select_favorite_movies(
        filter_china_movies=True, year_threshold=2020
    )
    print(f"结果: 找到 {len(favorite_ids)} 部电影")
