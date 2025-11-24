"""更新电影详情用解析器(由 get_movie_details 迁移并内联)"""

import json
from typing import Dict, Optional
from src.utils.logger import logger
from src.utils.date_utils import extract_year_from_release_date


class JsonWithSingleMovieExtraInfoParser:
    # * 注意, 时长可能为 0, 此时要标记为"暂无时长"; 导演可能为空, 此时标记为"暂无导演"
    def parse_json_with_single_movie_extra_info(
        self, json_content: str
    ) -> Optional[Dict]:
        """解析JSON内容，提取单个电影的额外信息

        Args:
            json_content (str): 电影详情API返回的JSON字符串。
                示例值: '{"data": {"movie": {"id": 123456, "nm": "肖申克的救赎", ...}}}'

        Returns:
            Optional[Dict]: 电影详情字典，包含以下字段：
                - id (int): 电影ID，例如: 123456
                - title (str): 电影标题，例如: "青爱"
                - release_year (str, 可选): 上映年份，例如: "2025"
                - director (str, 可选): 导演，例如: "向凯"
                - country (str, 可选): 制片国家，例如: "中国大陆"
                - language (str, 可选): 语言，例如: "国语"
                - duration (str, 可选): 时长，例如: "108min" 或 "暂无时长"
                - description (str, 可选): 剧情简介
            如果解析失败或JSON格式不正确，返回 None。
            示例返回值: {
                "id": 1502253,
                "title": "青爱",
                "release_year": "2025",
                "director": "向凯",
                "country": "中国大陆",
                "language": "国语",
                "duration": "108min",
                "description": "季杰幼年丧母，他对父亲季十三心怀深深的积怨..."
            }
        """
        try:
            # 检查内容是否为空
            if not json_content or not json_content.strip():
                logger.debug("JSON内容为空字符串")
                return None

            data = json.loads(json_content)
            if not data or "data" not in data or "movie" not in data["data"]:
                logger.debug("JSON数据结构不正确，缺少data.movie字段")
                return None

            movie_data = data["data"]["movie"]
            movie_details = self._extract_movie_details(movie_data)
            if movie_details:
                logger.debug(
                    f"成功解析电影详情: {movie_details.get('title', 'Unknown')}"
                )
                return movie_details
            else:
                logger.warning("解析电影详情失败")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"解析电影详情失败: {e}")
            return None

    def _normalize_field(self, value, default_text: str):
        """统一处理字段：如果为空(为 0, 为空字符串或者为 None)则设置为"暂无 xxx"

        Args:
            value: 字段值
            default_text: 默认文本，例如 "暂无导演"

        Returns:
            处理后的值
        """
        if value is None:
            return default_text
        if isinstance(value, str) and not value.strip():
            return default_text
        if isinstance(value, (int, float)) and value == 0:
            return default_text
        return value

    def _extract_movie_details(self, movie_data: Dict) -> Optional[Dict]:
        """从电影数据中提取详细信息

        Args:
            movie_data (Dict): 电影数据字典，来自 data.movie

        Returns:
            Optional[Dict]: 提取的电影详情字典
        """
        try:
            # 提取原始发行日期
            raw_release_date = (
                movie_data.get("releaseDate")
                or movie_data.get("frt")
                or movie_data.get("time")
                or movie_data.get("rt")
            )
            # 使用工具函数提取年份
            release_year = extract_year_from_release_date(raw_release_date)
            release_year = self._normalize_field(release_year, "暂无年份")

            # 提取语言字段，去除开头的逗号，并将英文逗号替换为中文逗号
            language = movie_data.get("oriLang")
            if language and isinstance(language, str):
                # * lstrip: 去除开头的字符
                language = language.lstrip(",")
                # 将英文逗号替换为中文逗号
                language = language.replace(",", "，")
            language = self._normalize_field(language, "暂无语言")

            # 提取导演字段，如果为空，则标记为"暂无导演"
            director = movie_data.get("dir")
            director = self._normalize_field(director, "暂无导演")

            # 提取时长字段，如果为 0 或 None，则标记为"暂无时长"（特殊逻辑：0 也要标记）
            # 如果时长是数字，在后面加上 "min"
            duration = movie_data.get("dur")
            if duration is None or duration == 0:
                duration = "暂无时长"
            elif isinstance(duration, (int, float)) and duration > 0:
                duration = f"{int(duration)}min"

            # 提取国家字段
            country = (
                movie_data.get("src")
                or movie_data.get("country")
                or movie_data.get("fra")
            )
            country = self._normalize_field(country, "暂无国家")

            # 提取描述字段
            description = movie_data.get("dra")
            description = self._normalize_field(description, "暂无简介")

            result: Dict = {
                "id": movie_data.get("id"),
                "title": movie_data.get("nm") or movie_data.get("title"),
                "release_year": release_year,
                "director": director,
                "country": country,
                "language": language,
                "duration": duration,
                "description": description,
            }
            return result
        except Exception as e:
            logger.error(f"提取电影详情失败: {e}")
            return None


json_with_single_movie_extra_info_parser = JsonWithSingleMovieExtraInfoParser()

if __name__ == "__main__":
    json_content = open(
        "data/demo/json_with_single_movie_extra_info.json",
        "r",
        encoding="utf-8",
    ).read()
    movie_details = json_with_single_movie_extra_info_parser.parse_json_with_single_movie_extra_info(
        json_content
    )
    print(movie_details)
