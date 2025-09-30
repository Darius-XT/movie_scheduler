"""选择喜爱电影并更新数据库标记"""

import logging

from .core.select_movie_selector import SelectMovieSelector
from src.db.db_operator import DBOperator
from src.logger import logger


def select_movie() -> tuple[int, int]:
    filter_china_movies = True
    year_threshold = 2020
    logger.info(
        f"开始选择喜爱电影，筛选条件: 过滤中国大陆={filter_china_movies}, 年份阈值={year_threshold}"
    )

    try:
        selector = SelectMovieSelector()
        favorite_movie_ids = selector.select_movies(
            filter_china_movies=filter_china_movies, year_threshold=year_threshold
        )

        if not favorite_movie_ids:
            logger.warning("没有找到符合条件的喜爱电影")
            return 0, 0

        logger.info(f"筛选完成，找到 {len(favorite_movie_ids)} 部喜爱电影")

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
    select_movie()
