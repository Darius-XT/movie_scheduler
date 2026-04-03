"""更新电影详情解析器。"""

from __future__ import annotations

import json
from typing import Any

from app.core.logger import logger
from app.use_cases.update.movie_info.extra_info.models import MovieExtraInfo


class MovieExtraInfoParser:
    """解析单部电影详情接口返回的 JSON 内容。"""

    def parse_details(self, json_content: str) -> MovieExtraInfo | None:
        """解析 JSON 内容并提取电影详情。"""
        try:
            if not json_content or not json_content.strip():
                logger.debug("电影详情 JSON 内容为空")
                return None

            data = json.loads(json_content)
            if not data or "data" not in data or "movie" not in data["data"]:
                logger.debug("电影详情 JSON 结构不正确，缺少 data.movie 字段")
                return None

            movie_data = data["data"]["movie"]
            movie_details = self._extract_movie_details(movie_data)
            if movie_details:
                logger.debug("成功解析电影详情，ID=%s", movie_details.id)
                return movie_details

            logger.warning("解析电影详情失败")
            return None
        except json.JSONDecodeError as error:
            logger.error("电影详情 JSON 解析失败: %s", error)
            return None
        except Exception as error:
            logger.error("解析电影详情失败: %s", error)
            return None

    def _normalize_field(self, value: Any, default_text: str) -> str | Any:
        """统一处理可能为空的字段。"""
        if value is None:
            return default_text
        if isinstance(value, str) and not value.strip():
            return default_text
        if isinstance(value, (int, float)) and value == 0:
            return default_text
        return value

    def _extract_movie_details(self, movie_data: dict[str, Any]) -> MovieExtraInfo | None:
        """从电影数据中提取统一结构的详情信息。"""
        try:
            language = movie_data.get("oriLang")
            if language and isinstance(language, str):
                language = language.lstrip(",").replace(",", "、")
            language = self._normalize_field(language, "暂无语言")

            director = self._normalize_field(movie_data.get("dir"), "暂无导演")

            duration = movie_data.get("dur")
            if duration is None or duration == 0:
                duration = "暂无时长"
            elif isinstance(duration, (int, float)) and duration > 0:
                duration = f"{int(duration)}min"

            country = movie_data.get("src") or movie_data.get("country") or movie_data.get("fra")
            country = self._normalize_field(country, "暂无国家")

            description = self._normalize_field(movie_data.get("dra"), "暂无简介")

            return MovieExtraInfo(
                id=movie_data.get("id"),
                director=str(director),
                country=str(country),
                language=str(language),
                duration=str(duration),
                description=str(description),
            )
        except Exception as error:
            logger.error("提取电影详情失败: %s", error)
            return None


movie_extra_info_parser = MovieExtraInfoParser()
