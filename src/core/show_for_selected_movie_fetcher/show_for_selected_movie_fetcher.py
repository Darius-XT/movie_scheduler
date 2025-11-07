"""获取选中电影的所有场次信息"""

import json
from typing import List, Dict
from src.db.db_operate_manager import db_operate_manager
from src.utils.logger import logger
from src.core.show_for_selected_movie_fetcher.html_with_all_movie_showdate_scraper import (
    html_with_all_movie_showdate_scraper,
)
from src.core.show_for_selected_movie_fetcher.html_with_all_movie_showdate_parser import (
    html_with_all_movie_showdate_parser,
)
from src.core.show_for_selected_movie_fetcher.json_with_batch_cinema_for_movie_and_date_scraper import (
    json_with_batch_cinema_for_movie_and_date_scraper,
)
from src.core.show_for_selected_movie_fetcher.json_with_batch_cinema_for_movie_and_date_parser import (
    json_with_batch_cinema_for_movie_and_date_parser,
)
from src.core.show_for_selected_movie_fetcher.json_with_all_show_for_cinema_scraper import (
    json_with_all_show_for_cinema_scraper,
)
from src.core.show_for_selected_movie_fetcher.json_with_all_show_for_cinema_parser import (
    json_with_all_show_for_cinema_parser,
)


class ShowForSelectedMovieFetcher:
    def __init__(self):
        pass

    def fetch_shows_for_selected_movies(self, movie_ids: List[int]) -> List[Dict]:
        """获取选中电影的所有场次信息

        Args:
            movie_ids (List[int]): 电影ID列表。
                示例值: [1505776, 1528086]

        Returns:
            List[Dict]: 嵌套结构的场次信息列表，格式如下：
                [
                    {
                        "movie_id": 1505776,
                        "movie_name": "即兴谋杀",
                        "release_year": "2024",
                        "director": "导演名",
                        "country": "国家",
                        "cinemas": [
                            {
                                "cinema_id": 17166,
                                "cinema_name": "上海枫泾天娱影城",
                                "shows": [
                                    {
                                        "date": "2025-11-10",
                                        "time": "18:00",
                                        "price": "33"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            如果解析失败或未找到场次，返回空列表 []。
            注意：release_year、director、country 可能为 None（如果数据库中不存在）。
        """
        result: List[Dict] = []

        logger.info(f"开始获取 {len(movie_ids)} 部电影的场次信息")

        for movie_id in movie_ids:
            try:
                logger.info(f"正在处理电影 ID: {movie_id}")

                # 从数据库获取电影信息
                movie_info = self._get_movie_info(movie_id)
                if not movie_info or not movie_info.get("movie_name"):
                    logger.warning(f"无法获取电影信息，跳过电影 ID: {movie_id}")
                    continue

                movie_name = movie_info["movie_name"]
                logger.debug(f"电影名称: {movie_name}")

                # 创建电影数据结构
                movie_data: Dict = {
                    "movie_id": movie_id,
                    "movie_name": movie_name,
                    "release_year": movie_info.get("release_year"),
                    "director": movie_info.get("director"),
                    "country": movie_info.get("country"),
                    "cinemas": {},
                }

                # 步骤1: 获取所有有排片的日期
                show_dates = self._get_show_dates(movie_id)
                if not show_dates:
                    logger.warning(
                        f"电影 {movie_name} (ID: {movie_id}) 没有找到排片日期"
                    )
                    continue

                logger.debug(f"找到 {len(show_dates)} 个排片日期: {show_dates}")

                # 步骤2: 对于每个日期，获取所有影院
                for show_date in show_dates:
                    logger.debug(f"处理日期: {show_date}")

                    # 获取该日期下的所有影院（遍历所有批次）
                    cinema_ids = self._get_all_cinemas_for_movie_and_date(
                        movie_id, show_date
                    )

                    if not cinema_ids:
                        logger.debug(f"日期 {show_date} 没有找到影院")
                        continue

                    logger.debug(f"找到 {len(cinema_ids)} 个影院")

                    # 步骤3: 对于每个影院，获取该电影的场次
                    for cinema_id in cinema_ids:
                        shows = self._get_shows_for_cinema(cinema_id, movie_name)

                        # 将场次添加到对应的影院中
                        for show in shows:
                            cinema_id_key = show.get("cinema_id")
                            cinema_name = show.get("cinema_name", "")

                            if cinema_id_key is None:
                                continue

                            # 如果影院不存在，创建影院数据结构
                            if cinema_id_key not in movie_data["cinemas"]:
                                movie_data["cinemas"][cinema_id_key] = {
                                    "cinema_id": cinema_id_key,
                                    "cinema_name": cinema_name,
                                    "shows": [],
                                }

                            # 添加场次信息（转换为目标格式）
                            movie_data["cinemas"][cinema_id_key]["shows"].append(
                                {
                                    "date": show.get("show_date", ""),
                                    "time": show.get("show_time", ""),
                                    "price": show.get("price", ""),
                                }
                            )

                # 将影院字典转换为列表
                movie_data["cinemas"] = list(movie_data["cinemas"].values())

                # 统计场次数量
                total_shows = sum(
                    len(cinema["shows"]) for cinema in movie_data["cinemas"]
                )

                logger.info(
                    f"电影 {movie_name} (ID: {movie_id}) 共找到 {total_shows} 个场次，分布在 {len(movie_data['cinemas'])} 个影院"
                )

                # 只添加有场次的电影
                if movie_data["cinemas"]:
                    result.append(movie_data)

            except Exception as e:
                logger.error(f"处理电影 ID {movie_id} 时发生错误: {e}")
                continue

        total_shows = sum(
            len(cinema["shows"]) for movie in result for cinema in movie["cinemas"]
        )
        logger.info(f"总共找到 {len(result)} 部电影，{total_shows} 个场次信息")

        # 格式化输出结果
        logger.info("场次信息结果:")
        formatted_result = json.dumps(result, ensure_ascii=False, indent=2)
        logger.info(formatted_result)

        return result

    def _get_movie_info(self, movie_id: int) -> Dict | None:
        """从数据库获取电影信息（包括名称、首映年份、导演、国家）"""
        try:
            movie = db_operate_manager.get_movie_by_id(movie_id)
            if not movie:
                return None

            # 获取首映年份（已经是年份格式）
            release_year = movie.release_year

            # 安全地获取字段值
            title_value = movie.title
            director_value = movie.director
            country_value = movie.country

            return {
                "movie_name": str(title_value) if title_value is not None else None,
                "release_year": release_year,
                "director": str(director_value) if director_value is not None else None,
                "country": str(country_value) if country_value is not None else None,
            }
        except Exception as e:
            logger.error(f"获取电影信息失败 (ID: {movie_id}): {e}")
            return None

    def _get_show_dates(self, movie_id: int) -> List[str]:
        """获取指定电影的所有有排片的日期"""
        try:
            success, html_content = (
                html_with_all_movie_showdate_scraper.scrape_html_with_all_movie_showdate(
                    movie_id
                )
            )

            if not success or not html_content:
                logger.warning(f"获取电影 {movie_id} 的排片日期失败")
                return []

            dates = (
                html_with_all_movie_showdate_parser.parse_html_with_all_movie_showdate(
                    html_content
                )
            )
            return dates
        except Exception as e:
            logger.error(f"获取排片日期失败 (电影 ID: {movie_id}): {e}")
            return []

    def _get_all_cinemas_for_movie_and_date(
        self, movie_id: int, show_date: str
    ) -> List[int]:
        """获取指定电影在指定日期的所有影院（遍历所有批次）"""
        all_cinema_ids: List[int] = []
        limit = 20
        offset = 0

        while True:
            try:
                success, json_content = (
                    json_with_batch_cinema_for_movie_and_date_scraper.scrape_json_with_batch_cinema_for_movie_and_date(
                        movie_id, show_date, None, limit, offset
                    )
                )

                if not success or not json_content:
                    logger.debug(
                        f"获取影院信息失败 (电影 ID: {movie_id}, 日期: {show_date}, offset: {offset})"
                    )
                    break

                cinema_ids = json_with_batch_cinema_for_movie_and_date_parser.parse_json_with_batch_cinema_for_movie_and_date(
                    json_content
                )

                if not cinema_ids:
                    # 没有更多影院了，停止遍历
                    break

                all_cinema_ids.extend(cinema_ids)
                offset += limit

                # 如果返回的影院数量少于 limit，说明已经是最后一页
                if len(cinema_ids) < limit:
                    break

            except Exception as e:
                logger.error(
                    f"获取影院信息失败 (电影 ID: {movie_id}, 日期: {show_date}, offset: {offset}): {e}"
                )
                break

        return all_cinema_ids

    def _get_shows_for_cinema(self, cinema_id: int, movie_name: str) -> List[Dict]:
        """获取指定影院中指定电影的所有场次"""
        try:
            success, json_content = (
                json_with_all_show_for_cinema_scraper.scrape_json_with_all_show_for_cinema(
                    cinema_id, None
                )
            )

            if not success or not json_content:
                logger.debug(f"获取影院 {cinema_id} 的场次信息失败")
                return []

            shows = json_with_all_show_for_cinema_parser.parse_json_with_all_show_for_cinema(
                json_content, movie_name
            )
            return shows
        except Exception as e:
            logger.error(
                f"获取场次信息失败 (影院 ID: {cinema_id}, 电影: {movie_name}): {e}"
            )
            return []


show_for_selected_movie_fetcher = ShowForSelectedMovieFetcher()

if __name__ == "__main__":
    movie_ids = [1502253, 1518611]
    shows = show_for_selected_movie_fetcher.fetch_shows_for_selected_movies(movie_ids)
    print(shows)
