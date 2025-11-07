"""解析指定电影在指定日期和城市的影院信息JSON数据"""

import json
from typing import List
from src.utils.logger import logger


class JsonWithBatchCinemaForMovieAndDateParser:
    def parse_json_with_batch_cinema_for_movie_and_date(
        self, json_content: str
    ) -> List[int]:
        """解析JSON内容，提取影院ID列表

        Args:
            json_content (str): 影院信息API返回的JSON字符串。
                示例值: '{"code": 0, "data": {"cinemas": [{"id": 17166, "name": "上海枫泾天娱影城", ...}]}}'

        Returns:
            List[int]: 影院ID列表。
            如果解析失败或JSON为空，返回空列表 []。
            示例返回值: [17166, 41216, 37630]
        """
        try:
            logger.debug("解析影院JSON内容")

            # 检查内容是否为空
            if not json_content or not json_content.strip():
                logger.debug("JSON内容为空字符串")
                return []

            # 解析JSON，如果解析后数据为空则返回空列表
            data = json.loads(json_content)
            if not data:
                logger.debug("JSON数据为空")
                return []

            # 检查响应格式
            if not isinstance(data, dict) or "data" not in data:
                logger.warning("JSON数据结构不正确，缺少data字段")
                return []

            data_section = data.get("data", {})
            if not isinstance(data_section, dict) or "cinemas" not in data_section:
                logger.warning("JSON数据结构不正确，缺少data.cinemas字段")
                return []

            cinemas_data = data_section.get("cinemas", [])
            if not isinstance(cinemas_data, list):
                logger.warning("cinemas字段不是列表格式")
                return []

            cinema_ids: List[int] = []
            for cinema_data in cinemas_data:
                if isinstance(cinema_data, dict):
                    cinema_id = cinema_data.get("id")
                    if cinema_id is not None:
                        cinema_ids.append(int(cinema_id))

            logger.debug(f"成功解析 {len(cinema_ids)} 个影院ID")
            return cinema_ids
        except json.JSONDecodeError as e:
            logger.error(f"解析JSON失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析影院列表失败: {e}")
            return []


json_with_batch_cinema_for_movie_and_date_parser = (
    JsonWithBatchCinemaForMovieAndDateParser()
)

if __name__ == "__main__":
    json_content = open(
        "data/demo/json_with_batch_cinema_for_movie_and_date.json",
        "r",
        encoding="utf-8",
    ).read()
    cinema_ids = json_with_batch_cinema_for_movie_and_date_parser.parse_json_with_batch_cinema_for_movie_and_date(
        json_content
    )
    print(cinema_ids)
