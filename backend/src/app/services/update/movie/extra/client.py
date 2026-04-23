"""电影额外信息客户端：合并 scraper + parser，对外返回业务对象。"""

from __future__ import annotations

import json
from typing import Any

import requests
import urllib3

from app.core.logger import logger
from app.services.update.movie.extra.entities import MovieExtraInfo

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MovieExtraInfoClient:
    """合并 HTTP 抓取与 JSON 解析，返回业务对象。"""

    def __init__(self) -> None:
        self.base_url = "https://apis.netstart.cn/maoyan/movie/intro"
        self.timeout = 30
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Referer": "https://www.maoyan.com/",
            "Origin": "https://www.maoyan.com",
        }

    def fetch_details(self, movie_id: int) -> MovieExtraInfo | None:
        """抓取并解析单部电影详情。

        Returns:
            None — HTTP 请求失败或解析失败。
            MovieExtraInfo — 解析成功的业务对象。
        """
        json_content = self._fetch(movie_id)
        if json_content is None:
            return None
        return self._parse(json_content)

    # ------------------------------------------------------------------
    # 私有：HTTP
    # ------------------------------------------------------------------

    def _fetch(self, movie_id: int) -> str | None:
        """发起 HTTP 请求，失败返回 None。"""
        try:
            url = f"{self.base_url}?movieId={movie_id}"
            logger.debug("开始获取电影详情: %s", url)

            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=False)

            logger.debug("响应状态码: %s", response.status_code)
            logger.debug("响应长度: %s 字符", len(response.text))

            if response.status_code == 200:
                logger.debug("成功获取电影详情信息")
                return response.text

            logger.warning("请求失败，状态码: %s", response.status_code)
            return None
        except Exception as error:
            logger.error("获取电影详情失败: %s", error)
            return None

    # ------------------------------------------------------------------
    # 私有：解析
    # ------------------------------------------------------------------

    def _parse(self, json_content: str) -> MovieExtraInfo | None:
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


movie_extra_info_client = MovieExtraInfoClient()
