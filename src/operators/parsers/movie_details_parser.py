"""解析电影详情JSON数据，提取电影详细信息"""

import json
from typing import Dict, Optional
from src.logger import logger


class MovieDetailsParser:
    def __init__(self):
        pass

    # 解析电影详情JSON数据, 返回一个包含电影详情的字典
    def parse_movie_details(self, json_content: str) -> Optional[Dict]:
        try:
            # 解析JSON
            data = json.loads(json_content)

            # 检查数据结构
            if not data or "data" not in data or "movie" not in data["data"]:
                logger.warning("JSON数据结构不正确，缺少data.movie字段")
                return None

            movie_data = data["data"]["movie"]

            # 提取电影详情信息
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

    def _extract_movie_details(self, movie_data: Dict) -> Optional[Dict]:
        """从电影数据中提取详细信息

        Args:
            movie_data: 电影原始数据

        Returns:
            Optional[Dict]: 提取的电影详情
        """
        try:
            id = movie_data.get("id")  # 电影ID
            title = movie_data.get("nm")  # 电影名称
            director = movie_data.get("dir", "")  # 导演
            country = movie_data.get("src", "")  # 制片国家
            language = movie_data.get("oriLang", "")  # 语言
            duration = movie_data.get("dur", 0)  # 时长(分钟)
            description = movie_data.get("dra", "")  # 剧情简介

            # 构建电影详情对象
            movie_details = {
                "id": id,
                "title": title,
                "director": director,
                "country": country,
                "language": language,
                "duration": duration,
                "description": description,
            }

            return movie_details

        except Exception as e:
            logger.error(f"提取电影详情失败: {e}")
            return None

    def is_valid_movie_data(self, json_content: str) -> bool:
        """检查JSON数据是否包含有效的电影信息

        Args:
            json_content: JSON字符串内容

        Returns:
            bool: 是否为有效的电影数据
        """
        try:
            data = json.loads(json_content)
            return (
                data
                and "data" in data
                and "movie" in data["data"]
                and data["data"]["movie"].get("id") is not None
            )
        except Exception:
            return False


# 创建解析器实例
movie_details_parser = MovieDetailsParser()

if __name__ == "__main__":
    with open("src/datas/demos/movie_details.json", "r", encoding="utf-8") as f:
        json_content = f.read()
    movie_details = movie_details_parser.parse_movie_details(json_content)
    print(movie_details)
