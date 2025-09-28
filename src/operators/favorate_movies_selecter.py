"""对数据库中更新后的电影进行筛选, 挑出外国电影 / 老电影"""

from typing import List
from src.db.db_connector import db_connector
from src.db.db_operator import DBOperator
from src.logger import logger
from datetime import datetime


class FavoriteMovieSelector:
    """喜爱电影选择器类"""

    def __init__(self):
        """初始化选择器"""
        self.china_keywords = [
            "中国",
            "中国大陆",
            "中国香港",
            "中国台湾",
            "中国澳门",
            "China",
            "Chinese",
            "Hong Kong",
            "Taiwan",
            "Macau",
        ]

    def get_favorite_movie_ids(self) -> List[int]:
        """获取喜爱电影ID列表

        Returns:
            List[int]: 喜爱电影的ID列表
        """
        logger.info("开始筛选喜爱电影...")

        try:
            with DBOperator(db_connector) as db_ops:
                # 获取所有电影
                all_movies = db_ops.get_all_movies()

                if not all_movies:
                    logger.warning("数据库中没有电影数据")
                    return []

                logger.info(f"数据库中总共有 {len(all_movies)} 部电影")

                favorite_ids = []

                for movie in all_movies:
                    movie_id = int(movie.id)  # type: ignore

                    # 检查是否符合喜爱条件
                    if self._is_favorite_movie(movie):
                        favorite_ids.append(movie_id)
                        logger.debug(f"选中喜爱电影: {movie.title} (ID: {movie_id})")

                logger.info(f"筛选完成，共找到 {len(favorite_ids)} 部喜爱电影")
                return favorite_ids

        except Exception as e:
            logger.error(f"筛选喜爱电影时发生异常: {e}")
            return []

    def _is_favorite_movie(self, movie) -> bool:
        """判断电影是否为喜爱电影

        Args:
            movie: 电影对象

        Returns:
            bool: 是否为喜爱电影
        """
        # 条件1: 国家不为中国大陆
        is_not_china = self._is_not_china_movie(movie)

        # 条件2: 上映时间早于2020年
        is_before_2020 = self._is_before_2020(movie)

        # 满足任一条件即为喜爱电影
        return is_not_china or is_before_2020

    def _is_not_china_movie(self, movie) -> bool:
        """判断是否为非中国大陆电影

        Args:
            movie: 电影对象

        Returns:
            bool: 是否为非中国大陆电影
        """
        if not movie.country:
            return False

        country = movie.country.strip()

        # 检查是否包含中国大陆关键词
        for keyword in self.china_keywords:
            if keyword in country:
                return False

        return True

    def _is_before_2020(self, movie) -> bool:
        """判断上映时间是否早于2020年

        Args:
            movie: 电影对象

        Returns:
            bool: 是否早于2020年
        """
        if not movie.release_date:
            return False

        try:
            # 解析上映日期
            release_date = datetime.strptime(movie.release_date, "%Y-%m-%d")
            return release_date.year < 2020
        except (ValueError, TypeError):
            # 如果日期格式不正确，尝试其他格式
            try:
                # 尝试 YYYY-MM 格式
                release_date = datetime.strptime(movie.release_date, "%Y-%m")
                return release_date.year < 2020
            except (ValueError, TypeError):
                # 尝试 YYYY 格式
                try:
                    release_date = datetime.strptime(movie.release_date, "%Y")
                    return release_date.year < 2020
                except (ValueError, TypeError):
                    logger.debug(f"无法解析上映日期: {movie.release_date}")
                    return False

    def get_favorite_movies_by_category(self) -> dict:
        """按类别获取喜爱电影

        Returns:
            dict: 包含不同类别喜爱电影的字典
        """
        logger.info("开始按类别筛选喜爱电影...")

        try:
            with DBOperator(db_connector) as db_ops:
                all_movies = db_ops.get_all_movies()

                if not all_movies:
                    return {"non_china": [], "before_2020": [], "both": [], "total": 0}

                non_china_ids = []
                before_2020_ids = []
                both_ids = []

                for movie in all_movies:
                    movie_id = int(movie.id)  # type: ignore

                    is_not_china = self._is_not_china_movie(movie)
                    is_before_2020 = self._is_before_2020(movie)

                    # 分别添加到对应的列表中
                    if is_not_china:
                        non_china_ids.append(movie_id)
                    if is_before_2020:
                        before_2020_ids.append(movie_id)
                    if is_not_china and is_before_2020:
                        both_ids.append(movie_id)

                # 计算正确的总数（避免重复计算）
                all_favorite_ids = set(non_china_ids + before_2020_ids)

                result = {
                    "non_china": non_china_ids,
                    "before_2020": before_2020_ids,
                    "both": both_ids,
                    "total": len(all_favorite_ids),
                }

                logger.info("按类别筛选完成:")
                logger.info(f"  非中国大陆电影: {len(non_china_ids)} 部")
                logger.info(f"  2020年前上映: {len(before_2020_ids)} 部")
                logger.info(f"  同时满足两个条件: {len(both_ids)} 部")
                logger.info(f"  总计: {result['total']} 部")

                return result

        except Exception as e:
            logger.error(f"按类别筛选喜爱电影时发生异常: {e}")
            return {"non_china": [], "before_2020": [], "both": [], "total": 0}


# 创建全局实例
favorite_moviesselector = FavoriteMovieSelector()


if __name__ == "__main__":
    import logging

    logger.setLevel(logging.INFO)

    # 测试基本功能
    favorite_ids = favorite_moviesselector.get_favorite_movie_ids()
    print(f"喜爱电影ID列表: {favorite_ids[:10]}...")  # 只显示前10个

    # 测试分类功能
    categories = favorite_moviesselector.get_favorite_movies_by_category()
    print(f"分类结果: {categories}")
