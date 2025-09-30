"""更新放映信息（由原 get_movie_showdate_list 与 get_movie_cinema_list 合并）"""

from src.db.db_operator import DBOperator
from .core.showdate_list_scraper import update_showdate_list_scraper
from .core.showdate_list_parser import update_showdate_list_parser
from .core.cinema_list_scraper import update_show_cinema_list_scraper
from .core.cinema_list_parser import update_show_cinema_list_parser
from src.logger import logger


def update_show_for_favorites() -> tuple[int, int, int]:
    logger.info("开始获取喜爱电影的放映日期列表...")

    try:
        with DBOperator() as db_op:
            favorite_movies = db_op.get_favorite_movies()

        if not favorite_movies:
            logger.warning("数据库中没有喜爱的电影")
            return 0, 0, 0

        logger.info(f"找到 {len(favorite_movies)} 部喜爱的电影")

        success_with_dates_count = 0
        success_no_dates_count = 0
        failure_count = 0

        for movie in favorite_movies:
            try:
                logger.debug(f"处理电影: {movie.title} (ID: {movie.id})")
                movie_id_value = movie.id
                success, html_content = (
                    update_showdate_list_scraper.scrape_movie_showdate_list(
                        movie_id=movie_id_value,  # type: ignore[arg-type]
                        city="上海",
                    )
                )

                if not success or not html_content:
                    logger.warning(f"电影 {movie.title} 的放映日期页面爬取失败")
                    failure_count += 1
                    continue

                show_dates = update_showdate_list_parser.parse_movie_showdate_list(
                    html_content
                )

                if not show_dates:
                    logger.info(f"电影 {movie.title} 暂未上映，没有找到放映日期")
                    success_no_dates_count += 1
                    continue

                logger.debug(
                    f"电影 {movie.title} 找到 {len(show_dates)} 个放映日期: {show_dates}"
                )

                schedules_data = []
                movie_id_value = movie.id
                movie_title_value = movie.title
                for show_date in show_dates:
                    schedule_data = {
                        "movie_id": movie_id_value,
                        "movie_title": movie_title_value,
                        "cinema_id": None,
                        "cinema_name": None,
                        "show_date": show_date,
                        "show_time": None,
                    }
                    schedules_data.append(schedule_data)

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


def update_show_for_movie(
    movie_id: int, show_date: str | None = None
) -> tuple[int, int]:
    logger.info(f"开始获取电影 {movie_id} 的影院放映信息...")

    try:
        if show_date is None:
            success, html_content = (
                update_show_cinema_list_scraper.scrape_movie_cinema_list(
                    movie_id=movie_id,
                    show_date=None,
                )
            )
        else:
            success, html_content = (
                update_show_cinema_list_scraper.scrape_movie_cinema_list(
                    movie_id=movie_id,
                    show_date=show_date,
                )
            )

        if not success or not html_content:
            logger.warning(f"获取电影 {movie_id} 的影院列表页面失败")
            return 0, 1

        cinema_list_data = update_show_cinema_list_parser.parse_movie_cinema_list(
            html_content
        )

        if not cinema_list_data:
            logger.warning(f"电影 {movie_id} 没有找到影院放映信息")
            return 0, 1

        logger.info(f"电影 {movie_id} 找到 {len(cinema_list_data)} 条影院放映信息")

        with DBOperator() as db_op:
            success_count, failure_count = db_op.save_movie_cinema_schedules_batch(
                cinema_list_data
            )

        logger.info(
            f"电影 {movie_id} 影院信息保存完成: 成功 {success_count} 条，失败 {failure_count} 条"
        )
        return success_count, failure_count

    except Exception as e:
        logger.error(f"获取电影 {movie_id} 影院放映信息时发生错误: {e}")
        return 0, 1
