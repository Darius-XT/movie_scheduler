"""更新电影列表（由原 get_movie_list 迁移）"""

from typing import Dict, List, Set, Any
from src.db.db_operate_manager import db_operate_manager
from src.core.info_update_manager.all_movie_info_updater.all_movie_base_info_updater.html_with_batch_movie_base_info_parser import (
    HtmlWithBatchMovieBaseInfoParser,
)
from src.utils.logger import logger
from src.core.info_update_manager.all_movie_info_updater.all_movie_base_info_updater.html_with_batch_movie_base_info_scraper import (
    HtmlWithBatchMovieBaseInfoScraper,
)


class AllMovieBaseInfoUpdater:
    def __init__(self):
        self.parser = HtmlWithBatchMovieBaseInfoParser()
        self.scraper = HtmlWithBatchMovieBaseInfoScraper()

    def update_all_movie_base_info(self) -> Dict[str, int]:
        """更新所有电影基础信息（从猫眼网站抓取电影列表）

        Returns:
            Dict[str, int]: 更新统计信息，包含以下字段：
                - added (int): 新增电影数量，例如: 5
                - removed (int): 删除电影数量（下架的电影），例如: 2
                - total (int): 当前数据库中的电影总数，例如: 150

            示例返回值:
                {
                    "added": 5,
                    "removed": 2,
                    "total": 150
                }
        """
        logger.info("开始抓取电影列表...")

        existing_movies = db_operate_manager.get_all_movies()
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

                success, html_content = (
                    self.scraper.scrape_html_with_batch_movie_base_info(show_type, page)
                )

                if not success or not html_content:
                    logger.warning(f"获取页面失败，跳过 page={page}")
                    break

                movies_data = self.parser.parse_html_with_batch_movie_base_info(
                    html_content
                )
                if not movies_data:
                    logger.debug(
                        f"{show_type_name}电影抓取完毕，共{page - 1}页（第{page}页未解析到数据）"
                    )
                    break

                type_movies.extend(movies_data)
                logger.debug(f"第{page}页: 解析到{len(movies_data)}部电影")
                page += 1

            logger.info(
                f"{show_type_name}列表页面抓取完成，共抓取{len(type_movies)}部电影"
            )
            all_scraped_movies.extend(type_movies)

        stats = self._perform_incremental_update(existing_movie_ids, all_scraped_movies)
        return stats

    def _perform_incremental_update(
        self, existing_movie_ids: Set[Any], scraped_movies: List[Dict]
    ) -> Dict[str, int]:
        """执行增量更新（添加新电影，删除下架电影）

        Args:
            existing_movie_ids (Set[Any]): 数据库中已存在的电影ID集合。
                示例值: {123456, 789012, 345678}
            scraped_movies (List[Dict]): 从网站抓取到的电影数据列表。
                每个字典包含以下字段：
                    - id (int): 电影ID，例如: 123456
                    - title (str): 电影标题，例如: "肖申克的救赎"
                    - score (str): 评分，例如: "9.7" 或 "暂无评分"
                    - genres (str, 可选): 类型，例如: "剧情/犯罪"
                    - actors (str, 可选): 主演，例如: "蒂姆·罗宾斯/摩根·弗里曼"
                    - release_year (str, 可选): 上映年份，例如: "1994"
                示例值: [
                    {
                        "id": 123456,
                        "title": "肖申克的救赎",
                        "score": "9.7",
                        "genres": "剧情/犯罪",
                        "actors": "蒂姆·罗宾斯/摩根·弗里曼",
                        "release_year": "1994"
                    }
                ]

        Returns:
            Dict[str, int]: 更新统计信息，包含以下字段：
                - added (int): 新增电影数量，例如: 5
                - removed (int): 删除电影数量，例如: 2
                - total (int): 当前数据库中的电影总数，例如: 150

            示例返回值:
                {
                    "added": 5,
                    "removed": 2,
                    "total": 150
                }
        """
        scraped_movie_ids = {movie["id"] for movie in scraped_movies}

        added_movie_ids = scraped_movie_ids - existing_movie_ids
        removed_movie_ids = existing_movie_ids - scraped_movie_ids

        added_count = 0
        for movie in scraped_movies:
            if movie["id"] in added_movie_ids:
                if db_operate_manager.save_movie(movie):
                    added_count += 1
                    logger.info(f"添加新电影: {movie['title']} (ID: {movie['id']})")

        removed_count = 0
        for movie_id in removed_movie_ids:
            movie = db_operate_manager.get_movie_by_id(movie_id)
            if movie and db_operate_manager.delete_movie(movie_id):
                removed_count += 1
                logger.info(f"删除下架电影: title={movie.title}, ID={movie_id}")

        final_count = db_operate_manager.get_movies_count()

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


all_movie_base_info_updater = AllMovieBaseInfoUpdater()

if __name__ == "__main__":
    all_movie_base_info_updater.update_all_movie_base_info()
