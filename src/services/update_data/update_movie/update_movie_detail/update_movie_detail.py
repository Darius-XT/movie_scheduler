"""更新电影详情（由原 get_movie_details 迁移）"""

from src.db.db_connector import db_connector
from src.db.db_operator import DBOperator
from .core.movie_details_scraper import update_movie_detail_scraper
from .core.movie_details_parser import update_movie_detail_parser
from src.logger import logger


def update_movie_detail() -> int:
    logger.info("开始获取电影详细信息...")

    success_count = 0
    failure_count = 0

    try:
        with DBOperator(db_connector) as db_ops:
            movies_without_details = db_ops.get_movies_without_details()

            if not movies_without_details:
                logger.info("没有需要补充详情的电影（所有电影都有详细信息）")
                return 0

            logger.info(
                f"找到 {len(movies_without_details)} 部需要补充详情的电影，开始获取详情..."
            )

            for movie in movies_without_details:
                movie_id = int(movie.id)  # type: ignore
                logger.debug(f"正在获取电影详情: {movie.title} (ID: {movie_id})")

                try:
                    success, json_content = (
                        update_movie_detail_scraper.scrape_movie_details(movie_id)
                    )

                    if not success or not json_content:
                        logger.warning(
                            f"获取电影详情失败: {movie.title} (ID: {movie_id})"
                        )
                        failure_count += 1
                        continue

                    movie_details = update_movie_detail_parser.parse_movie_details(
                        json_content
                    )

                    if not movie_details:
                        logger.warning(
                            f"解析电影详情失败: {movie.title} (ID: {movie_id})"
                        )
                        failure_count += 1
                        continue

                    if movie_details.get("id") != movie_id:
                        logger.error(
                            f"电影ID不匹配: 数据库ID={movie_id}, 解析ID={movie_details.get('id')}"
                        )
                        failure_count += 1
                        continue

                    if movie_details.get("title") != movie.title:
                        logger.warning(
                            f"电影标题不匹配: 数据库标题='{movie.title}', 解析标题='{movie_details.get('title')}'"
                        )
                        movie_details["title"] = movie.title

                    if db_ops.save_movie(movie_details):
                        logger.debug(
                            f"成功更新电影详情: {movie.title} (ID: {movie_id})"
                        )
                        success_count += 1
                    else:
                        logger.error(
                            f"保存电影详情失败: {movie.title} (ID: {movie_id})"
                        )
                        failure_count += 1

                except Exception as e:
                    logger.error(
                        f"处理电影 {movie.title} (ID: {movie_id}) 时发生异常: {e}"
                    )
                    failure_count += 1
                    continue

    except Exception as e:
        logger.error(f"获取电影详情过程中发生异常: {e}")
        return success_count

    logger.info(
        "电影详情获取完成, 成功: %d 部, 失败: %d 部, 总计: %d 部",
        success_count,
        failure_count,
        success_count + failure_count,
    )

    return success_count
