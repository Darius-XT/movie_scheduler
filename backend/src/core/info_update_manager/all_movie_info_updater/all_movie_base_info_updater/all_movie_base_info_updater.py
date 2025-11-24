"""更新电影列表（由原 get_movie_list 迁移）"""

from typing import Dict, List, Set, Any, Callable, Optional
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

    def update_all_movie_base_info(
        self,
        city_id: int = 10,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, int]:
        """更新所有电影基础信息（从猫眼网站抓取电影列表）

        Args:
            city_id (int): 城市ID。
                默认为 10（上海）。
                示例值: 1, 10
            progress_callback (callable, 可选): 进度回调函数。
                回调函数接收一个参数: (message: str)
                - message: 进度消息，如 "正在抓取电影列表"

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
        logger.info(f"开始更新电影基础信息（城市ID: {city_id}）...")

        if progress_callback:
            progress_callback("正在抓取电影列表")

        existing_movies = db_operate_manager.get_all_movies()
        existing_movie_ids = {movie.id for movie in existing_movies}
        logger.debug(f"数据库中当前有 {len(existing_movie_ids)} 部电影")

        all_scraped_movies: List[Dict] = []
        showing_movie_ids: Set[int] = set()  # 记录所有"正在热映"的电影ID

        for show_type in range(1, 3):
            show_type_name = "正在热映" if show_type == 1 else "即将上映"
            logger.debug(f"开始抓取{show_type_name}电影...")

            page = 1
            type_movies: List[Dict] = []

            while True:
                logger.debug(f"抓取{show_type_name}第{page}页")

                success, html_content = (
                    self.scraper.scrape_html_with_batch_movie_base_info(
                        show_type, page, city_id
                    )
                )

                if not success or not html_content:
                    logger.warning(f"获取页面失败，跳过 page={page}")
                    break

                movies_data, is_expected_empty = (
                    self.parser.parse_html_with_batch_movie_base_info(html_content)
                )
                if is_expected_empty:
                    logger.debug(f"{show_type_name}电影抓取完毕，共{page - 1}页")
                    break

                elif not movies_data:
                    logger.error(f"发生意外错误: 第{page}页未解析到数据，结束抓取")
                    break

                # 记录"正在热映"的电影ID
                if show_type == 1:
                    for m in movies_data:
                        if m.get("id") is not None:
                            showing_movie_ids.add(m["id"])

                type_movies.extend(movies_data)
                logger.debug(f"第{page}页: 解析到{len(movies_data)}部电影")
                page += 1

            logger.info(
                f"{show_type_name}列表页面抓取完成，共抓取{len(type_movies)}部电影"
            )
            all_scraped_movies.extend(type_movies)

        # 根据是否在"正在热映"列表中设置 is_showing
        # 规则：当且仅当电影出现在"正在热映"列表时，is_showing = True
        #       否则（在"即将上映"列表或两个列表都没有），is_showing = False
        for movie in all_scraped_movies:
            movie_id = movie.get("id")
            if movie_id is not None:
                movie["is_showing"] = movie_id in showing_movie_ids

        # 统计抓取结果：正在热映、即将上映、重复数
        scraped_total = len(all_scraped_movies)
        scraped_ids = [
            m.get("id") for m in all_scraped_movies if m.get("id") is not None
        ]
        unique_scraped_ids = set(scraped_ids)
        duplicate_count = scraped_total - len(unique_scraped_ids)
        showing_ids = showing_movie_ids
        upcoming_ids = {
            m["id"]
            for m in all_scraped_movies
            if m.get("id") is not None and m.get("id") not in showing_movie_ids
        }

        stats = self._perform_incremental_update(existing_movie_ids, all_scraped_movies)

        # 汇总打印：原本有多少部、抓取到正在热映多少部、即将上映多少部、重复多少部、
        # 去重后实际上新增多少部、删除多少部、当前总数多少部
        logger.info(
            "基础电影信息更新统计: 原有=%d, 正在热映=%d, 即将上映=%d, 重复=%d, 新增=%d, 删除=%d, 当前总数=%d",
            len(existing_movie_ids),
            len(showing_ids),
            len(upcoming_ids),
            duplicate_count,
            stats.get("added", 0),
            stats.get("removed", 0),
            stats.get("total", 0),
        )
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
        existing_but_updated_ids = (
            scraped_movie_ids & existing_movie_ids
        )  # 已存在但需要更新的电影

        added_count = 0
        for movie in scraped_movies:
            if movie["id"] in added_movie_ids:
                if db_operate_manager.save_movie(movie):
                    added_count += 1
                    logger.info(f"添加新电影: {movie['title']} (ID: {movie['id']})")

        # 更新已存在电影的 is_showing 状态和其他基础信息
        # 规则：当且仅当电影出现在"正在热映"列表时，is_showing = True
        #       当且仅当发现电影不存在于"正在热映"列表时，is_showing = False
        updated_count = 0
        for movie in scraped_movies:
            if movie["id"] in existing_but_updated_ids:
                existing_movie = db_operate_manager.get_movie_by_id(movie["id"])
                if existing_movie:
                    # 更新 is_showing 和其他基础信息字段
                    # 即使 is_showing 值相同，也要更新其他可能变化的基础信息（如 title, score 等）
                    update_data = {
                        "id": movie["id"],
                        "is_showing": movie.get("is_showing", False),
                        "title": movie.get("title"),
                        "score": movie.get("score"),
                        "genres": movie.get("genres"),
                        "actors": movie.get("actors"),
                        "release_year": movie.get("release_year"),
                    }
                    if db_operate_manager.save_movie(update_data):
                        updated_count += 1
                        if existing_movie.is_showing != movie.get("is_showing", False):
                            logger.info(
                                f"更新电影状态: {movie.get('title', 'Unknown')} (ID: {movie['id']}), "
                                f"is_showing: {existing_movie.is_showing} -> {movie.get('is_showing', False)}"
                            )
                        else:
                            logger.debug(
                                f"更新电影基础信息: {movie.get('title', 'Unknown')} (ID: {movie['id']})"
                            )

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

        return stats


all_movie_base_info_updater = AllMovieBaseInfoUpdater()

if __name__ == "__main__":
    all_movie_base_info_updater.update_all_movie_base_info()
