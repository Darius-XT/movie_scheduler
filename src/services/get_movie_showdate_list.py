"""获取喜爱电影的放映日期列表服务"""

import logging
from src.db.db_operator import DBOperator
from src.operators.scrapers.movie_showdate_list_scraper import (
    movie_showdate_list_scraper,
)
from src.operators.parsers.movie_showdate_list_parser import (
    parser as movie_showdate_parser,
)
from src.logger import logger


# 获取所有喜爱电影的放映日期列表并保存到数据库, 返回三种状态的数量
def get_favorite_movies_showdate_lists() -> tuple[int, int, int]:
    """获取所有喜爱电影的放映日期列表并保存到数据库

    Returns:
        tuple[int, int, int]: (成功且找到放映日期, 成功但暂未上映, 失败)
    """
    logger.info("开始获取喜爱电影的放映日期列表...")

    try:
        # 获取所有喜爱的电影
        with DBOperator() as db_op:
            favorite_movies = db_op.get_favorite_movies()

        if not favorite_movies:
            logger.warning("数据库中没有喜爱的电影")
            return 0, 0, 0

        logger.info(f"找到 {len(favorite_movies)} 部喜爱的电影")

        success_with_dates_count = 0  # 成功且找到放映日期
        success_no_dates_count = 0  # 成功但暂未上映
        failure_count = 0  # 失败

        # 为每部喜爱电影获取放映日期列表
        for movie in favorite_movies:
            try:
                logger.debug(f"处理电影: {movie.title} (ID: {movie.id})")

                # 爬取该电影的放映日期页面
                movie_id_value = movie.id
                success, html_content = (
                    movie_showdate_list_scraper.scrape_movie_showdate_list(
                        movie_id=movie_id_value,  # type: ignore[arg-type]
                        city="上海",
                    )
                )

                if not success or not html_content:
                    logger.warning(f"电影 {movie.title} 的放映日期页面爬取失败")
                    failure_count += 1
                    continue

                # 解析放映日期列表
                show_dates = movie_showdate_parser.parse_movie_showdate_list(
                    html_content
                )

                if not show_dates:
                    logger.info(f"电影 {movie.title} 暂未上映，没有找到放映日期")
                    success_no_dates_count += 1
                    continue

                logger.debug(
                    f"电影 {movie.title} 找到 {len(show_dates)} 个放映日期: {show_dates}"
                )

                # 构建放映场次数据（先用电影和放映日期占位，后续补充影院信息及详细时间信息）
                schedules_data = []
                movie_id_value = movie.id
                movie_title_value = movie.title
                for show_date in show_dates:
                    schedule_data = {
                        "movie_id": movie_id_value,
                        "movie_title": movie_title_value,
                        "cinema_id": None,  # 先占位, 后续补充
                        "cinema_name": None,  # 先占位, 后续补充
                        "show_date": show_date,
                        "show_time": None,  # 先占位, 后续补充
                    }
                    schedules_data.append(schedule_data)

                # 批量保存到数据库
                with DBOperator() as db_op:
                    success_saved, failure_saved = (
                        db_op.save_movie_cinema_schedules_batch(schedules_data)
                    )

                if success_saved > 0:
                    logger.info(
                        f"电影 {movie.title} 成功保存 {success_saved} 个放映场次"
                    )
                    success_with_dates_count += 1
                else:
                    logger.warning(f"电影 {movie.title} 保存放映场次失败")
                    failure_count += 1

            except Exception as e:
                logger.error(f"处理电影 {movie.title} 时发生错误: {e}")
                failure_count += 1

        logger.info(
            f"放映日期列表获取完成: 成功且找到放映日期 {success_with_dates_count} 部，"
            f"成功但暂未上映 {success_no_dates_count} 部，失败 {failure_count} 部"
        )
        return success_with_dates_count, success_no_dates_count, failure_count

    except Exception as e:
        logger.error(f"获取喜爱电影放映日期列表时发生错误: {e}")
        return 0, 0, 0


if __name__ == "__main__":
    logger.setLevel(logging.INFO)

    get_favorite_movies_showdate_lists()
