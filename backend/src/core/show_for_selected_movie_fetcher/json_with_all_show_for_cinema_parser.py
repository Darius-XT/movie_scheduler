"""解析指定影院的所有场次信息JSON数据，根据电影名称筛选"""

import json
from typing import List, Dict, Optional
from src.utils.logger import logger


class JsonWithAllShowForCinemaParser:
    def parse_json_with_all_show_for_cinema(
        self, json_content: str, movie_name: str
    ) -> List[Dict]:
        """解析JSON内容，根据电影名称筛选出所有指定电影的场次信息

        Args:
            json_content (str): 影院场次信息API返回的JSON字符串。
                示例值: '{"code": 0, "data": {"movies": [{"nm": "即兴谋杀", "shows": [...]}]}}'
            movie_name (str): 电影名称，用于筛选场次。
                示例值: "即兴谋杀"

        Returns:
            List[Dict]: 场次信息列表，每个字典包含以下字段：
                - movie_id (int): 电影ID，例如: 1505776
                - movie_name (str): 电影名称，例如: "即兴谋杀"
                - show_date (str): 放映日期，格式为 YYYY-MM-DD，例如: "2025-11-10"
                - show_time (str): 放映时间，格式为 HH:MM，例如: "18:00"
                - price (str): 价格，例如: "33"
                - cinema_id (int): 影院ID，例如: 17166
                - cinema_name (str): 影院名称，例如: "上海枫泾天娱影城"
            如果解析失败或未找到指定电影，返回空列表 []。
            示例返回值: [
                {
                    "movie_id": 1505776,
                    "movie_name": "即兴谋杀",
                    "show_date": "2025-11-10",
                    "show_time": "18:00",
                    "price": "33",
                    "cinema_id": 17166,
                    "cinema_name": "上海枫泾天娱影城"
                }
            ]
        """
        try:
            logger.debug(f"解析影院场次JSON内容，筛选电影: {movie_name}")

            # 检查内容是否为空
            if not json_content or not json_content.strip():
                logger.debug("JSON内容为空字符串")
                return []

            # 解析JSON
            data = json.loads(json_content)
            if not data:
                logger.debug("JSON数据为空")
                return []

            # 检查响应格式
            if not isinstance(data, dict) or "data" not in data:
                logger.warning("JSON数据结构不正确，缺少data字段")
                return []

            data_section = data.get("data", {})
            if not isinstance(data_section, dict):
                logger.warning("data字段不是字典格式")
                return []

            # 获取影院ID和名称
            cinema_id = data_section.get("cinemaId")
            cinema_name = data_section.get("cinemaName", "")

            # 获取电影列表
            movies = data_section.get("movies", [])
            if not isinstance(movies, list):
                logger.warning("movies字段不是列表格式")
                return []

            # 查找指定电影
            target_movie = None
            for movie in movies:
                if isinstance(movie, dict):
                    movie_nm = movie.get("nm", "")
                    if movie_nm == movie_name:
                        target_movie = movie
                        break

            if not target_movie:
                logger.warning(f"未找到电影: {movie_name}")
                return []

            # 提取场次信息
            shows = target_movie.get("shows", [])
            if not isinstance(shows, list):
                logger.warning("shows字段不是列表格式")
                return []

            movie_id = target_movie.get("id")
            show_list: List[Dict] = []

            for show_date_group in shows:
                if not isinstance(show_date_group, dict):
                    continue

                show_date = show_date_group.get("showDate", "")
                plist = show_date_group.get("plist", [])

                if not isinstance(plist, list):
                    continue

                for show_item in plist:
                    if not isinstance(show_item, dict):
                        continue

                    show_info = self._extract_show_info(
                        show_item,
                        movie_id,
                        movie_name,
                        show_date,
                        cinema_id,
                        cinema_name,
                    )
                    if show_info:
                        show_list.append(show_info)

            logger.debug(f"成功解析 {len(show_list)} 个场次信息")
            return show_list
        except json.JSONDecodeError as e:
            logger.error(f"解析JSON失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析场次信息失败: {e}")
            return []

    def _extract_show_info(
        self,
        show_item: Dict,
        movie_id: Optional[int],
        movie_name: str,
        show_date: str,
        cinema_id: Optional[int],
        cinema_name: str,
    ) -> Optional[Dict]:
        """从单个场次数据中提取信息

        Args:
            show_item (Dict): 单个场次的原始数据字典
            movie_id (Optional[int]): 电影ID
            movie_name (str): 电影名称
            show_date (str): 放映日期
            cinema_id (Optional[int]): 影院ID
            cinema_name (str): 影院名称

        Returns:
            Optional[Dict]: 提取的场次信息字典，如果提取失败则返回 None
        """
        try:
            show_info: Dict = {}
            show_info["movie_id"] = movie_id
            show_info["movie_name"] = movie_name
            show_info["show_date"] = show_date
            show_info["show_time"] = show_item.get("tm", "")
            show_info["price"] = show_item.get("discountSellPrice", "0")
            show_info["cinema_id"] = cinema_id
            show_info["cinema_name"] = cinema_name

            return show_info
        except Exception as e:
            logger.error(f"解析场次数据失败: {e}")
            return None


json_with_all_show_for_cinema_parser = JsonWithAllShowForCinemaParser()

if __name__ == "__main__":
    json_content = open(
        "data/demo/json_with_all_show_for_cinema.json",
        "r",
        encoding="utf-8",
    ).read()
    movie_name = "即兴谋杀"
    show_list = (
        json_with_all_show_for_cinema_parser.parse_json_with_all_show_for_cinema(
            json_content, movie_name
        )
    )
    print(show_list)
