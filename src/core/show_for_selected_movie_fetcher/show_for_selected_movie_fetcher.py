"""获取选中电影的所有场次信息"""

import json
import asyncio
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from src.db.db_operate_manager import db_operate_manager
from src.utils.logger import logger
from src.config_manager import config_manager
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
    def __init__(self, max_workers: int = 10):
        """初始化场次获取器

        Args:
            max_workers (int): 线程池最大工作线程数，用于并行执行网络请求。
                默认为 10。
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    # * 回调函数的被调用方, 将回调函数作为参数传入，用于在获取场次信息时，更新进度
    # * 在这个函数内部, 需要定义"当执行到某处时, 更新并返回给调用方的回调消息(就是 progress_callback 参数)的格式与内容"
    def fetch_shows_for_selected_movies(
        self, movie_ids: List[int], progress_callback=None, use_async: bool = True
    ) -> List[Dict]:
        """获取选中电影的所有场次信息（支持同步和异步两种模式）

        Args:
            movie_ids (List[int]): 电影ID列表。
                示例值: [1505776, 1528086]
            progress_callback (callable, optional): 进度回调函数，接收进度信息字典
            use_async (bool): 是否使用异步模式。默认为 True。
                异步模式可以大幅提升性能，特别是在处理多个电影时。

        Returns:
            List[Dict]: 嵌套结构的场次信息列表
        """
        if use_async:
            return asyncio.run(
                self._fetch_shows_for_selected_movies_async(
                    movie_ids, progress_callback
                )
            )
        else:
            return self._fetch_shows_for_selected_movies_sync(
                movie_ids, progress_callback
            )

    def _fetch_shows_for_selected_movies_sync(
        self, movie_ids: List[int], progress_callback=None
    ) -> List[Dict]:
        """获取选中电影的所有场次信息

        Args:
            movie_ids (List[int]): 电影ID列表。
                示例值: [1505776, 1528086]
            progress_callback (callable, optional): 进度回调函数，接收进度信息字典

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

                # 通知进度：找到的日期
                if progress_callback:
                    progress_callback(
                        {
                            "type": "dates_found",
                            "dates": show_dates,
                            "movie_id": movie_id,
                        }
                    )

                # 步骤2: 对于每个日期，获取所有影院
                for date_idx, show_date in enumerate(show_dates):
                    logger.debug(f"处理日期: {show_date}")

                    # 通知进度：开始处理某个日期
                    if progress_callback:
                        progress_callback(
                            {
                                "type": "processing_date",
                                "date": show_date,
                                "date_idx": date_idx + 1,
                                "total_dates": len(show_dates),
                                "movie_id": movie_id,
                            }
                        )

                    # 获取该日期下的所有影院（遍历所有批次）
                    cinema_ids = self._get_all_cinemas_for_movie_and_date(
                        movie_id, show_date
                    )

                    if not cinema_ids:
                        logger.debug(f"日期 {show_date} 没有找到影院")
                        continue

                    logger.debug(f"找到 {len(cinema_ids)} 个影院")

                    # 步骤3: 对于每个影院，获取该电影的场次（串行处理）
                    for cinema_idx, cinema_id in enumerate(cinema_ids):
                        # 通知进度：正在处理某个影院
                        if progress_callback:
                            progress_callback(
                                {
                                    "type": "processing_cinema",
                                    "date": show_date,
                                    "cinema_idx": cinema_idx + 1,
                                    "total_cinemas": len(cinema_ids),
                                    "cinema_id": cinema_id,
                                    "movie_id": movie_id,
                                }
                            )

                        shows = self._get_shows_for_cinema(cinema_id, movie_name)

                        # 将场次添加到对应的影院中
                        self._merge_shows_to_movie_data(movie_data, shows)

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

    async def _fetch_shows_for_selected_movies_async(
        self, movie_ids: List[int], progress_callback=None
    ) -> List[Dict]:
        """异步获取选中电影的所有场次信息"""
        result: List[Dict] = []

        logger.info(f"开始异步获取 {len(movie_ids)} 部电影的场次信息")

        # 并行处理所有电影
        tasks = [
            self._process_single_movie_async(movie_id, progress_callback)
            for movie_id in movie_ids
        ]
        movie_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 收集成功的结果
        for movie_result in movie_results:
            if isinstance(movie_result, Exception):
                logger.error(f"处理电影时发生错误: {movie_result}")
                continue
            if isinstance(movie_result, dict) and movie_result.get("cinemas"):
                result.append(movie_result)

        total_shows = sum(
            len(cinema["shows"]) for movie in result for cinema in movie["cinemas"]
        )
        logger.info(f"总共找到 {len(result)} 部电影，{total_shows} 个场次信息")

        # 格式化输出结果
        logger.info("场次信息结果:")
        formatted_result = json.dumps(result, ensure_ascii=False, indent=2)
        logger.info(formatted_result)

        return result

    async def _process_single_movie_async(
        self, movie_id: int, progress_callback=None
    ) -> Optional[Dict]:
        """异步处理单个电影的所有场次信息"""
        try:
            logger.info(f"正在处理电影 ID: {movie_id}")

            # 从数据库获取电影信息（同步操作，但很快）
            movie_info = self._get_movie_info(movie_id)
            if not movie_info or not movie_info.get("movie_name"):
                logger.warning(f"无法获取电影信息，跳过电影 ID: {movie_id}")
                return None

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
            show_dates = await asyncio.to_thread(self._get_show_dates, movie_id)
            if not show_dates:
                logger.warning(f"电影 {movie_name} (ID: {movie_id}) 没有找到排片日期")
                return None

            logger.debug(f"找到 {len(show_dates)} 个排片日期: {show_dates}")

            # 通知进度：找到的日期
            if progress_callback:
                progress_callback(
                    {
                        "type": "dates_found",
                        "dates": show_dates,
                        "movie_id": movie_id,
                    }
                )

            # 步骤2: 对于每个日期，并行获取所有影院和场次
            date_tasks = [
                self._process_single_date_async(
                    movie_id,
                    movie_name,
                    show_date,
                    date_idx,
                    len(show_dates),
                    progress_callback,
                )
                for date_idx, show_date in enumerate(show_dates)
            ]
            date_results = await asyncio.gather(*date_tasks, return_exceptions=True)

            # 合并所有日期的结果
            for date_result in date_results:
                if isinstance(date_result, Exception):
                    logger.error(f"处理日期时发生错误: {date_result}")
                    continue
                if isinstance(date_result, dict):
                    self._merge_cinemas_to_movie_data(movie_data, date_result)

            # 将影院字典转换为列表
            movie_data["cinemas"] = list(movie_data["cinemas"].values())

            # 统计场次数量
            total_shows = sum(len(cinema["shows"]) for cinema in movie_data["cinemas"])

            logger.info(
                f"电影 {movie_name} (ID: {movie_id}) 共找到 {total_shows} 个场次，分布在 {len(movie_data['cinemas'])} 个影院"
            )

            return movie_data

        except Exception as e:
            logger.error(f"处理电影 ID {movie_id} 时发生错误: {e}")
            return None

    async def _process_single_date_async(
        self,
        movie_id: int,
        movie_name: str,
        show_date: str,
        date_idx: int,
        total_dates: int,
        progress_callback=None,
    ) -> Optional[Dict]:
        """异步处理单个日期的所有影院和场次"""
        try:
            logger.debug(f"处理日期: {show_date}")

            # 通知进度：开始处理某个日期
            if progress_callback:
                progress_callback(
                    {
                        "type": "processing_date",
                        "date": show_date,
                        "date_idx": date_idx + 1,
                        "total_dates": total_dates,
                        "movie_id": movie_id,
                    }
                )

            # 获取该日期下的所有影院（遍历所有批次，需要串行）
            cinema_ids = await asyncio.to_thread(
                self._get_all_cinemas_for_movie_and_date, movie_id, show_date
            )

            if not cinema_ids:
                logger.debug(f"日期 {show_date} 没有找到影院")
                return None

            logger.debug(f"找到 {len(cinema_ids)} 个影院")

            # 并行获取所有影院的场次信息
            cinema_tasks = [
                self._get_shows_for_cinema_async(
                    cinema_id,
                    movie_name,
                    show_date,
                    cinema_idx,
                    len(cinema_ids),
                    progress_callback,
                    movie_id,
                )
                for cinema_idx, cinema_id in enumerate(cinema_ids)
            ]
            cinema_results = await asyncio.gather(*cinema_tasks, return_exceptions=True)

            # 合并所有影院的结果
            result_cinemas = {}
            for cinema_result in cinema_results:
                if isinstance(cinema_result, Exception):
                    logger.error(f"获取影院场次时发生错误: {cinema_result}")
                    continue
                if isinstance(cinema_result, list):
                    for show in cinema_result:
                        cinema_id_key = show.get("cinema_id")
                        if cinema_id_key is None:
                            continue
                        if cinema_id_key not in result_cinemas:
                            result_cinemas[cinema_id_key] = {
                                "cinema_id": cinema_id_key,
                                "cinema_name": show.get("cinema_name", ""),
                                "shows": [],
                            }
                        result_cinemas[cinema_id_key]["shows"].append(
                            {
                                "date": show.get("show_date", ""),
                                "time": show.get("show_time", ""),
                                "price": show.get("price", ""),
                            }
                        )

            return result_cinemas

        except Exception as e:
            logger.error(f"处理日期 {show_date} 时发生错误: {e}")
            return None

    async def _get_shows_for_cinema_async(
        self,
        cinema_id: int,
        movie_name: str,
        show_date: str,
        cinema_idx: int,
        total_cinemas: int,
        progress_callback=None,
        movie_id: Optional[int] = None,
    ) -> List[Dict]:
        """异步获取指定影院中指定电影的所有场次"""
        # 通知进度：正在处理某个影院
        if progress_callback and movie_id is not None:
            progress_callback(
                {
                    "type": "processing_cinema",
                    "date": show_date,
                    "cinema_idx": cinema_idx + 1,
                    "total_cinemas": total_cinemas,
                    "cinema_id": cinema_id,
                    "movie_id": movie_id,
                }
            )

        shows = await asyncio.to_thread(
            self._get_shows_for_cinema, cinema_id, movie_name
        )
        return shows

    def _merge_shows_to_movie_data(self, movie_data: Dict, shows: List[Dict]):
        """将场次信息合并到电影数据中"""
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

    def _merge_cinemas_to_movie_data(self, movie_data: Dict, cinemas: Dict):
        """将影院信息合并到电影数据中"""
        for cinema_id, cinema_info in cinemas.items():
            if cinema_id not in movie_data["cinemas"]:
                movie_data["cinemas"][cinema_id] = cinema_info
            else:
                # 合并场次列表
                movie_data["cinemas"][cinema_id]["shows"].extend(cinema_info["shows"])

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
        city_id = config_manager.city_id or 10

        while True:
            try:
                success, json_content = (
                    json_with_batch_cinema_for_movie_and_date_scraper.scrape_json_with_batch_cinema_for_movie_and_date(
                        movie_id, show_date, city_id, limit, offset
                    )
                )

                if not success or not json_content:
                    logger.debug(
                        f"获取影院信息失败 (电影 ID: {movie_id}, 日期: {show_date}, offset: {offset})"
                    )
                    break

                cinema_ids, is_last_page = (
                    json_with_batch_cinema_for_movie_and_date_parser.parse_json_with_batch_cinema_for_movie_and_date(
                        json_content
                    )
                )

                if is_last_page:
                    # 检测到 hasMore 为 false，这是最后一页
                    logger.debug(
                        f"检测到最后一页 (电影 ID: {movie_id}, 日期: {show_date}, offset: {offset})"
                    )
                    if cinema_ids:
                        all_cinema_ids.extend(cinema_ids)
                    break

                elif not cinema_ids:
                    logger.error(
                        f"发生意外错误: offset: {offset}未解析到数据，结束抓取"
                    )
                    break

                all_cinema_ids.extend(cinema_ids)
                offset += limit

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
