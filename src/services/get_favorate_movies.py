"""喜爱电影选择服务"""

import logging

from src.operators.favorate_movies_selecter import FavoriteMovieSelector
from src.db.db_operator import DBOperator
from src.logger import logger


# 获取喜爱电影并更新数据库的标记字段, 返回成功和失败的数量
def get_favorite_movies() -> tuple[int, int]:
    filter_china_movies = True
    year_threshold = 2020
    logger.info(
        f"开始选择喜爱电影，筛选条件: 过滤中国大陆={filter_china_movies}, 年份阈值={year_threshold}"
    )

    try:
        # 创建筛选器实例
        selector = FavoriteMovieSelector()

        # 筛选喜爱电影
        favorite_movie_ids = selector.select_favorite_movies(
            filter_china_movies=filter_china_movies, year_threshold=year_threshold
        )

        if not favorite_movie_ids:
            logger.warning("没有找到符合条件的喜爱电影")
            return 0, 0

        logger.info(f"筛选完成，找到 {len(favorite_movie_ids)} 部喜爱电影")

        # 更新数据库中的喜爱状态
        with DBOperator() as db_op:
            success_count, failure_count = db_op.update_movies_favorite_status(
                favorite_movie_ids
            )

        logger.info(f"数据库更新完成: 成功 {success_count} 部，失败 {failure_count} 部")
        return success_count, failure_count

    except Exception as e:
        logger.error(f"选择喜爱电影时发生错误: {e}")
        return 0, 0


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)

    get_favorite_movies()
