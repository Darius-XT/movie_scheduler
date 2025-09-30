"""获取指定类型的所有电影(包括爬取, 解析, 更新数据库的完整流程)"""

from src.db.db_connector import db_connector
from src.db.db_operator import DBOperator
from src.operators.parsers.movie_list_parser import movie_list_parser
from src.logger import logger
from src.operators.scrapers.movie_list_scraper import movie_list_scraper
from typing import Dict, List, Set, Any
import logging


def get_movie_list() -> Dict[str, int]:
    """获取所有电影并进行增量更新

    Returns:
        Dict[str, int]: 包含统计信息的字典
    """
    logger.info("开始抓取电影列表...")

    # 获取当前数据库中的所有电影ID
    with DBOperator(db_connector) as db_ops:
        existing_movies = db_ops.get_all_movies()
        existing_movie_ids = {movie.id for movie in existing_movies}
        logger.info(f"数据库中当前有 {len(existing_movie_ids)} 部电影")

    # 抓取所有电影
    all_scraped_movies = []

    # 遍历所有电影类型
    for show_type in range(1, 3):
        show_type_name = "正在热映" if show_type == 1 else "即将上映"
        logger.debug(f"开始抓取{show_type_name}电影...")

        page = 1
        type_movies = []

        # 对每种类型进行分页抓取
        while True:
            logger.debug(f"抓取{show_type_name}第{page}页")

            try:
                # 获取HTML内容
                success, html_content = movie_list_scraper.scrape_movie_list(
                    show_type, page
                )

                if not success or not html_content:
                    logger.warning(f"获取页面失败，跳过 page={page}")
                    break

                # 检查是否为空页面(为空则结束抓取)
                if movie_list_parser.is_empty_page(html_content):
                    logger.debug(f"{show_type_name}电影抓取完毕，共{page - 1}页")
                    break

                # 解析电影数据
                movies_data = movie_list_parser.parse_movie_list(html_content)

                if not movies_data:
                    logger.error(
                        f"第{page}页通过了空白页面检测, 但未解析到电影数据，结束抓取"
                    )
                    break

                type_movies.extend(movies_data)
                logger.debug(f"第{page}页: 解析到{len(movies_data)}部电影")

                # 准备下一页
                page += 1

            except Exception as e:
                logger.error(f"抓取第{page}页异常: {e}")
                break

        logger.info(f"{show_type_name}列表页面抓取完成，共抓取{len(type_movies)}部电影")
        all_scraped_movies.extend(type_movies)

    # 进行增量更新
    stats = _perform_incremental_update(existing_movie_ids, all_scraped_movies)

    return stats


def _perform_incremental_update(
    existing_movie_ids: Set[Any], scraped_movies: List[Dict]
) -> Dict[str, int]:
    """执行增量更新并返回统计信息

    Args:
        existing_movie_ids: 数据库中现有的电影ID集合
        scraped_movies: 抓取到的电影数据列表

    Returns:
        Dict[str, int]: 统计信息
    """
    scraped_movie_ids = {movie["id"] for movie in scraped_movies}

    # 计算差异
    added_movie_ids = scraped_movie_ids - existing_movie_ids
    removed_movie_ids = existing_movie_ids - scraped_movie_ids

    # 执行数据库操作
    with DBOperator(db_connector) as db_ops:
        # 1. 添加新电影
        added_count = 0
        for movie in scraped_movies:
            if movie["id"] in added_movie_ids:
                if db_ops.save_movie(movie):
                    added_count += 1
                    logger.info(f"添加新电影: {movie['title']} (ID: {movie['id']})")

        # 2. 删除下架电影
        removed_count = 0
        for movie_id in removed_movie_ids:
            movie = db_ops.get_movie_by_id(movie_id)
            if movie and db_ops.delete_movie(movie_id):
                removed_count += 1
                logger.info(f"删除下架电影: title={movie.title}, ID={movie_id}")

        # 3. 获取最终统计
        final_count = db_ops.get_movies_count()

    # 返回统计信息
    stats = {
        "added": added_count,
        "removed": removed_count,
        "total": final_count,
    }

    logger.info(
        "列表更新完成, 新增: %d 部, 删除: %d 部, 当前总数: %d 部",
        stats["added"],
        stats["removed"],
        stats["total"],
    )

    return stats


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)

    get_movie_list()
