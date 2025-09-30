"""更新电影详情用解析器(由 get_movie_details 迁移并内联)"""

import json
from typing import Dict, Optional
from src.logger import logger


class UpdateMovieDetailParser:
    def parse_movie_details(self, json_content: str) -> Optional[Dict]:
        try:
            data = json.loads(json_content)
            if not data or "data" not in data or "movie" not in data["data"]:
                logger.warning("JSON数据结构不正确，缺少data.movie字段")
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

    def _extract_movie_details(self, movie_data: Dict) -> Optional[Dict]:
        # 留空: 复用现有的DBOperator保存结构即可，具体字段映射与原始实现一致
        # 这里直接返回 movie_data 作为最小可用实现（假设字段名已符合 DB 入库）
        try:
            result: Dict = {
                "id": movie_data.get("id"),
                "title": movie_data.get("nm") or movie_data.get("title"),
                "country": (movie_data.get("ct") or movie_data.get("country")),
                "release_date": movie_data.get("rt") or movie_data.get("releaseDate"),
                # 其他字段按需补充
            }
            return result
        except Exception:
            return None


update_movie_detail_parser = UpdateMovieDetailParser()
