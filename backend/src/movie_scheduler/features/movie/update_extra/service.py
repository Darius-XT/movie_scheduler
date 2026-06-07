"""电影额外详情更新子领域 (爬猫眼 intro 接口 → 写 movies 详细字段)。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, cast

import requests
import urllib3

from movie_scheduler.core.logging import logger
from movie_scheduler.features.movie.models import MovieWriteData
from movie_scheduler.features.movie.repository import movie_repository
from movie_scheduler.features.movie.update_base.service import UpdateBaseProgressEvent

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_EXTRA_API_BASE = "https://apis.netstart.cn/maoyan/movie/intro"
_EXTRA_API_TIMEOUT = 30
_EXTRA_REQUEST_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Referer": "https://www.maoyan.com/",
    "Origin": "https://www.maoyan.com",
}


@dataclass(slots=True)
class _MovieExtraInfo:
    id: int | None
    director: str
    country: str
    language: str
    duration: str
    description: str


class UpdateExtraService:
    """爬猫眼 movie/intro 抓取额外详情(导演/国家/语言/片长/简介)。"""

    # ---------- 对外: 批量更新 ----------

    async def update_all(
        self,
        progress_callback: Callable[[UpdateBaseProgressEvent], None] | None = None,
    ) -> int:
        """更新电影额外详情,返回成功数量。"""
        logger.info("开始获取电影详情信息")
        movies_to_update = await asyncio.to_thread(movie_repository.get_movies_without_details)
        if not movies_to_update:
            logger.info("没有需要更新详情的电影")
            return 0

        total = len(movies_to_update)
        tasks = [
            self._process_single(idx=idx, total=total, movie=movie, progress_callback=progress_callback)
            for idx, movie in enumerate(movies_to_update, start=1)
        ]
        results = await asyncio.gather(*tasks)
        success_count = sum(1 for s in results if s)
        logger.info(
            "额外电影信息更新统计: 成功=%d, 失败=%d, 总计=%d",
            success_count, total - success_count, total,
        )
        return success_count

    # ---------- 内部: 单部处理 ----------

    async def _process_single(
        self,
        *,
        idx: int,
        total: int,
        movie: object,
        progress_callback: Callable[[UpdateBaseProgressEvent], None] | None,
    ) -> bool:
        movie_id = cast(int, getattr(movie, "id"))
        movie_title = cast(str | None, getattr(movie, "title", None))
        if progress_callback is not None:
            progress_callback(UpdateBaseProgressEvent(
                message=f"正在补充详细信息 ({idx}/{total})",
                stage="fetching_movie_details",
                current=idx, total=total,
            ))
        try:
            details = await asyncio.to_thread(self._fetch_details, movie_id)
            if details is None:
                logger.warning("获取或解析电影详情失败: %s (ID: %s)", movie_title, movie_id)
                return False
            ok = await asyncio.to_thread(
                movie_repository.save_movie,
                cast(MovieWriteData, asdict(details)),
            )
            if ok:
                logger.debug("成功更新电影详情: %s (ID: %s)", movie_title, movie_id)
                return True
            logger.error("保存电影详情失败: %s (ID: %s)", movie_title, movie_id)
            return False
        except Exception as error:
            logger.error("处理电影 %s (ID: %s) 时发生异常: %s", movie_title, movie_id, error)
            return False

    # ---------- 内部: 抓取 + 解析 ----------

    def _fetch_details(self, movie_id: int) -> _MovieExtraInfo | None:
        json_content = self._http_get(movie_id)
        if json_content is None:
            return None
        return self._parse(json_content)

    def _http_get(self, movie_id: int) -> str | None:
        url = f"{_EXTRA_API_BASE}?movieId={movie_id}"
        try:
            response = requests.get(url, headers=_EXTRA_REQUEST_HEADERS, timeout=_EXTRA_API_TIMEOUT, verify=False)
            if response.status_code == 200:
                return response.text
            logger.error(
                "获取电影详情请求失败: status=%s, url=%s, response=%s",
                response.status_code, url, response.text[:1000],
            )
            return None
        except Exception as error:
            logger.error("获取电影详情异常: url=%s, error=%s", url, error, exc_info=True)
            return None

    def _parse(self, json_content: str) -> _MovieExtraInfo | None:
        try:
            if not json_content or not json_content.strip():
                return None
            data = json.loads(json_content)
            if not data or "data" not in data or "movie" not in data["data"]:
                return None
            return self._extract(data["data"]["movie"])
        except json.JSONDecodeError as error:
            logger.error("电影详情 JSON 解析失败: %s", error)
            return None
        except Exception as error:
            logger.error("解析电影详情失败: %s", error)
            return None

    def _extract(self, movie_data: dict[str, Any]) -> _MovieExtraInfo | None:
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

            return _MovieExtraInfo(
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

    def _normalize_field(self, value: Any, default_text: str) -> str | Any:
        if value is None:
            return default_text
        if isinstance(value, str) and not value.strip():
            return default_text
        if isinstance(value, (int, float)) and value == 0:
            return default_text
        return value


update_extra_service = UpdateExtraService()
