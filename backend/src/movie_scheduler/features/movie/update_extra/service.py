"""电影额外详情更新子领域 (爬猫眼 intro 接口 → 写 movies 详细字段)。"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, cast

import requests
import urllib3

from movie_scheduler.config import config_manager
from movie_scheduler.core.logging import logger
from movie_scheduler.core.request_logging import log_external_http_request
from movie_scheduler.features.movie.models import MovieWriteData
from movie_scheduler.features.movie.repository import movie_repository
from movie_scheduler.features.movie.update_base.service import UpdateBaseProgressEvent
from movie_scheduler.shared.maoyan import build_maoyan_mobile_headers

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_EXTRA_PAGE_BASE = "https://www.maoyan.com/films"
_EXTRA_API_TIMEOUT = 30


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
        movies_to_update = await asyncio.to_thread(movie_repository.get_all_movies)
        if not movies_to_update:
            logger.info("没有可更新详情的电影")
            return 0

        total = len(movies_to_update)
        tasks = [
            self._process_single(idx=idx, total=total, movie=movie, progress_callback=progress_callback)
            for idx, movie in enumerate(movies_to_update, start=1)
        ]
        results = await asyncio.gather(*tasks)
        success_count = sum(1 for s in results if s)
        logger.info(
            "额外电影信息更新统计: 更新=%d, 跳过或失败=%d, 总计=%d",
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
            update_data = self._build_update_data(movie, details, movie_id)
            if update_data is None:
                logger.debug("电影详情无变化,跳过保存: %s (ID: %s)", movie_title, movie_id)
                return False
            ok = await asyncio.to_thread(movie_repository.save_movie, update_data)
            if ok:
                logger.debug("成功更新电影详情: %s (ID: %s)", movie_title, movie_id)
                return True
            logger.error("保存电影详情失败: %s (ID: %s)", movie_title, movie_id)
            return False
        except Exception as error:
            logger.error("处理电影 %s (ID: %s) 时发生异常: %s", movie_title, movie_id, error)
            return False

    # ---------- 内部: 抓取 + 解析 ----------

    def _build_update_data(
        self,
        movie: object,
        details: _MovieExtraInfo,
        movie_id: int,
    ) -> MovieWriteData | None:
        update_data = cast(MovieWriteData, asdict(details))
        update_data["id"] = movie_id
        changed = False
        for field_name in ("director", "country", "language", "duration", "description"):
            current = getattr(movie, field_name, None)
            incoming = update_data.get(field_name)
            if not self._same_text(current, incoming):
                changed = True
                break
        return update_data if changed else None

    def _same_text(self, left: object, right: object) -> bool:
        return str(left or "").strip() == str(right or "").strip()

    def _fetch_details(self, movie_id: int) -> _MovieExtraInfo | None:
        html_content = self._http_get(movie_id)
        if html_content is None:
            return None
        return self._parse(html_content)

    def _http_get(self, movie_id: int) -> str | None:
        url = f"{_EXTRA_PAGE_BASE}/{movie_id}"
        try:
            log_external_http_request("GET", url, purpose="获取电影详情页面")
            response = requests.get(
                url,
                headers=build_maoyan_mobile_headers(city_id=config_manager.city_id, hot_movie_ids=[movie_id]),
                timeout=_EXTRA_API_TIMEOUT,
                verify=False,
            )
            if response.status_code == 200:
                return response.text
            logger.error(
                "获取电影详情页面失败: status=%s, response=%s",
                response.status_code, response.text[:1000],
            )
            return None
        except Exception as error:
            logger.error("获取电影详情页面异常: error=%s", error, exc_info=True)
            return None

    def _parse(self, html_content: str) -> _MovieExtraInfo | None:
        try:
            if not html_content or not html_content.strip() or "猫眼验证中心" in html_content:
                return None
            movie_data = self._extract_embedded_movie(html_content)
            if movie_data is None:
                return None
            return self._extract(movie_data)
        except Exception as error:
            logger.error("解析电影详情失败: %s", error)
            return None

    def _extract_embedded_movie(self, html_content: str) -> dict[str, Any] | None:
        match = re.search(r'"movie"\s*:\s*\{', html_content)
        if match is None:
            return None
        start = html_content.find("{", match.start())
        raw_json = self._slice_json_object(html_content, start)
        if raw_json is None:
            return None
        try:
            parsed = json.loads(raw_json)
            return cast(dict[str, Any], parsed) if isinstance(parsed, dict) else None
        except json.JSONDecodeError as error:
            logger.error("电影详情嵌入 JSON 解析失败: %s", error)
            return None

    def _slice_json_object(self, content: str, start: int) -> str | None:
        if start < 0 or start >= len(content) or content[start] != "{":
            return None
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(content)):
            char = content[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return content[start:index + 1]
        return None

    def _extract(self, movie_data: dict[str, Any]) -> _MovieExtraInfo | None:
        try:
            language = movie_data.get("oriLang")
            if language and isinstance(language, str):
                language = language.lstrip(",").replace(",", "、")
            language = self._normalize_field(language, "暂无语言")

            director = self._normalize_field(movie_data.get("dir") or movie_data.get("director"), "暂无导演")

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
