"""豆瓣 API 客户端。"""

from __future__ import annotations

from typing import cast

import requests

from app.core.config import config_manager
from app.core.logger import logger
from app.update.movie.douban.entities import DoubanMovieSearchItem


class DoubanApiClient:
    """负责调用已部署的 douban_api 服务。"""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url_override = base_url

    @property
    def base_url(self) -> str:
        return self._base_url_override or config_manager.douban_api_base_url

    @property
    def timeout(self) -> int:
        return config_manager.timeout or 60

    def search_movies(self, title: str, page: int = 1) -> list[DoubanMovieSearchItem]:
        """按电影标题搜索豆瓣候选项。"""
        normalized_title = title.strip()
        if not normalized_title:
            return []

        url = f"{self.base_url}/movie/list"
        try:
            response = requests.get(
                url,
                params={"key": normalized_title, "page": page},
                data={"key": normalized_title},
                timeout=self.timeout,
            )
        except Exception as error:
            logger.error(
                "调用豆瓣 API 搜索异常: title=%s, url=%s, error=%s",
                normalized_title,
                url,
                error,
                exc_info=True,
            )
            return []

        if not response.ok:
            logger.error(
                "调用豆瓣 API 搜索请求失败: title=%s, status=%s, url=%s, response=%s",
                normalized_title,
                response.status_code,
                url,
                response.text[:1000],
            )
            return []

        try:
            payload = cast(object, response.json())
        except Exception as error:
            logger.error(
                "豆瓣 API 响应 JSON 解析失败: title=%s, url=%s, response=%s, error=%s",
                normalized_title,
                url,
                response.text[:1000],
                error,
                exc_info=True,
            )
            return []

        if not isinstance(payload, dict):
            logger.warning("豆瓣 API 返回结构异常: title=%s", normalized_title)
            return []

        payload_dict = cast(dict[str, object], payload)
        raw_items = payload_dict.get("data")
        if not isinstance(raw_items, list):
            logger.warning("豆瓣 API 返回结构异常: title=%s", normalized_title)
            return []

        typed_raw_items = cast(list[object], raw_items)
        candidates: list[DoubanMovieSearchItem] = []
        for raw_item in typed_raw_items:
            if not isinstance(raw_item, dict):
                continue
            candidate = self._build_search_item(cast(dict[str, object], raw_item))
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    def _build_search_item(self, raw_item: dict[str, object]) -> DoubanMovieSearchItem | None:
        title = str(raw_item.get("title") or "").strip()
        cover_link = str(raw_item.get("cover_link") or "").strip()
        if not title or not cover_link:
            return None

        raw_actors = raw_item.get("actors")
        actors: list[str] = []
        if isinstance(raw_actors, list):
            typed_raw_actors = cast(list[object], raw_actors)
            for actor in typed_raw_actors:
                actor_text = str(actor).strip()
                if actor_text:
                    actors.append(actor_text)

        return DoubanMovieSearchItem(
            title=title,
            rating=str(raw_item.get("rating") or "").strip(),
            cover_link=cover_link,
            year=str(raw_item.get("year") or "").strip(),
            country=str(raw_item.get("country") or "").strip(),
            actors=actors,
        )


douban_api_client = DoubanApiClient()
