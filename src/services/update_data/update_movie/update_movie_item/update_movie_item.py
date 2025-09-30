"""更新电影列表（由原 get_movie_list 迁移）"""

from typing import Dict, List, Set, Any
from src.db.db_connector import db_connector
from src.db.db_operator import DBOperator
from .core.movie_list_parser import update_movie_item_parser
from src.logger import logger
from .core.movie_list_scraper import update_movie_item_scraper


def update_movie_item() -> Dict[str, int]:
    logger.info("开始抓取电影列表...")

    with DBOperator(db_connector) as db_ops:
        existing_movies = db_ops.get_all_movies()
        existing_movie_ids = {movie.id for movie in existing_movies}
        logger.info(f"数据库中当前有 {len(existing_movie_ids)} 部电影")

    all_scraped_movies: List[Dict] = []

    for show_type in range(1, 3):
        show_type_name = "正在热映" if show_type == 1 else "即将上映"
        logger.debug(f"开始抓取{show_type_name}电影...")

        page = 1
        type_movies: List[Dict] = []

        while True:
            logger.debug(f"抓取{show_type_name}第{page}页")

            success, html_content = update_movie_item_scraper.scrape_movie_list(
                show_type, page
            )

            if not success or not html_content:
                logger.warning(f"获取页面失败，跳过 page={page}")
                break

            if update_movie_item_parser.is_empty_page(html_content):
                logger.debug(f"{show_type_name}电影抓取完毕，共{page - 1}页")
                break

            movies_data = update_movie_item_parser.parse_movie_list(html_content)
            if not movies_data:
                logger.error(
                    f"第{page}页通过了空白页面检测, 但未解析到电影数据，结束抓取"
                )
                break

            type_movies.extend(movies_data)
            logger.debug(f"第{page}页: 解析到{len(movies_data)}部电影")
            page += 1

        logger.info(f"{show_type_name}列表页面抓取完成，共抓取{len(type_movies)}部电影")
        all_scraped_movies.extend(type_movies)

    stats = _perform_incremental_update(existing_movie_ids, all_scraped_movies)
    return stats


def _perform_incremental_update(
    existing_movie_ids: Set[Any], scraped_movies: List[Dict]
) -> Dict[str, int]:
    scraped_movie_ids = {movie["id"] for movie in scraped_movies}

    added_movie_ids = scraped_movie_ids - existing_movie_ids
    removed_movie_ids = existing_movie_ids - scraped_movie_ids

    with DBOperator(db_connector) as db_ops:
        added_count = 0
        for movie in scraped_movies:
            if movie["id"] in added_movie_ids:
                if db_ops.save_movie(movie):
                    added_count += 1
                    logger.info(f"添加新电影: {movie['title']} (ID: {movie['id']})")

        removed_count = 0
        for movie_id in removed_movie_ids:
            movie = db_ops.get_movie_by_id(movie_id)
            if movie and db_ops.delete_movie(movie_id):
                removed_count += 1
                logger.info(f"删除下架电影: title={movie.title}, ID={movie_id}")

        final_count = db_ops.get_movies_count()

    stats: Dict[str, int] = {
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
