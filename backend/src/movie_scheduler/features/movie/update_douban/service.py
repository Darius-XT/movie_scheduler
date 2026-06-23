"""电影豆瓣信息更新子领域 (爬豆瓣移动版搜索 → 写 movies.score/douban_url)。"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from movie_scheduler.config import config_manager
from movie_scheduler.core.logging import logger
from movie_scheduler.features.movie.models import MovieWriteData
from movie_scheduler.features.movie.repository import movie_repository
from movie_scheduler.features.movie.update_base.service import UpdateBaseProgressEvent

_DOUBAN_MOBILE_SEARCH_URL = "https://m.douban.com/search/"
_DOUBAN_MOBILE_BASE_URL = "https://m.douban.com"
_DOUBAN_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}
_MAX_SEARCH_ATTEMPTS = 2
_MAX_CONCURRENCY = 2


@dataclass(slots=True)
class _DoubanSearchItem:
    title: str
    rating: str
    cover_link: str
    year: str
    country: str
    actors: list[str]


@dataclass(slots=True)
class DoubanMovieSupplement:
    """补充后的豆瓣评分与详情链接。"""

    score: str
    douban_url: str | None


class SupportsDoubanMatchingMovie(Protocol):
    """支持豆瓣匹配所需字段的电影视图。"""

    @property
    def title(self) -> str | None: ...

    @property
    def release_date(self) -> str | None: ...

    @property
    def actors(self) -> str | None: ...


class UpdateDoubanService:
    """爬豆瓣移动版搜索为电影补充评分 + 详情链接,并支持批量更新。"""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url_override = base_url
        self.session = requests.Session()

    @property
    def base_url(self) -> str:
        return (self._base_url_override or _DOUBAN_MOBILE_SEARCH_URL).rstrip("/")

    @property
    def timeout(self) -> int:
        return config_manager.timeout or 60

    # ---------- 对外: 单部电影抓取 ----------

    def fetch_movie_supplement(self, movie: SupportsDoubanMatchingMovie) -> DoubanMovieSupplement:
        title = (movie.title or "").strip()
        if not title:
            return DoubanMovieSupplement(score="无豆瓣评分", douban_url=None)

        candidates = self._search_movies(title=title, page=1)
        if not candidates:
            logger.debug("豆瓣搜索无结果: %s", title)
            return DoubanMovieSupplement(score="无豆瓣评分", douban_url=None)

        best = self._choose_best_candidate(movie, candidates)
        if best is None:
            logger.debug("豆瓣搜索未找到可信匹配: %s", title)
            return DoubanMovieSupplement(score="无豆瓣评分", douban_url=None)

        return DoubanMovieSupplement(
            score=best.rating or "无豆瓣评分",
            douban_url=best.cover_link,
        )

    # ---------- 对外: 批量更新 ----------

    async def update_all(
        self,
        progress_callback: Callable[[UpdateBaseProgressEvent], None] | None = None,
    ) -> int:
        """更新电影豆瓣信息(增量),返回成功数量。"""
        logger.info("开始获取待补充豆瓣信息的电影")
        movies_to_update = await asyncio.to_thread(movie_repository.get_all_movies)
        if not movies_to_update:
            logger.info("没有可更新豆瓣信息的电影")
            return 0

        total = len(movies_to_update)
        semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)

        async def process(idx: int, movie: object) -> bool:
            async with semaphore:
                return await self._process_single(idx, total, movie, progress_callback)

        results = await asyncio.gather(*[process(i, m) for i, m in enumerate(movies_to_update, start=1)])
        success_count = sum(1 for s in results if s)
        logger.info(
            "豆瓣电影信息更新统计: 更新=%d, 跳过或失败=%d, 总计=%d",
            success_count, total - success_count, total,
        )
        return success_count

    # ---------- 对外: 单条抓取 + 持久化(供 service.fetch_douban_for_movie 使用) ----------

    async def update_one(self, movie: object) -> DoubanMovieSupplement:
        supplement = await asyncio.to_thread(
            self.fetch_movie_supplement, cast(SupportsDoubanMatchingMovie, movie),
        )
        await asyncio.to_thread(
            movie_repository.save_movie,
            cast(MovieWriteData, {
                "id": cast(int, getattr(movie, "id")),
                "title": cast(str | None, getattr(movie, "title", None)),
                "score": supplement.score,
                "douban_url": supplement.douban_url,
            }),
        )
        return supplement

    # ---------- 内部: 单部处理 ----------

    async def _process_single(
        self,
        index: int,
        total: int,
        movie: object,
        progress_callback: Callable[[UpdateBaseProgressEvent], None] | None,
    ) -> bool:
        movie_id = cast(int, getattr(movie, "id"))
        movie_title = cast(str | None, getattr(movie, "title", None))
        if progress_callback is not None:
            progress_callback(UpdateBaseProgressEvent(
                message=f"正在补充豆瓣信息 ({index}/{total})",
                stage="fetching_movie_douban_info",
                current=index, total=total,
            ))
        try:
            supplement = await asyncio.to_thread(
                self.fetch_movie_supplement, cast(SupportsDoubanMatchingMovie, movie),
            )
            update_data = self._build_update_data(movie, supplement, movie_id)
            if update_data is None:
                logger.debug("电影豆瓣信息无变化,跳过保存: %s (ID: %s)", movie_title, movie_id)
                return False
            ok = await asyncio.to_thread(movie_repository.save_movie, update_data)
            if ok:
                logger.debug("成功更新电影豆瓣信息: %s (ID: %s)", movie_title, movie_id)
                return True
            logger.error("保存电影豆瓣信息失败: %s (ID: %s)", movie_title, movie_id)
            return False
        except Exception as error:
            logger.error("处理电影 %s (ID: %s) 的豆瓣信息时发生异常: %s", movie_title, movie_id, error)
            return False

    # ---------- 内部: 抓取 + 解析 ----------

    def _build_update_data(
        self,
        movie: object,
        supplement: DoubanMovieSupplement,
        movie_id: int,
    ) -> MovieWriteData | None:
        current_score = getattr(movie, "score", None)
        current_url = getattr(movie, "douban_url", None)
        incoming_score = supplement.score
        incoming_url = supplement.douban_url

        update_data: MovieWriteData = {"id": movie_id}
        if self._should_update_score(current_score, incoming_score):
            update_data["score"] = incoming_score
        if self._should_update_url(current_url, incoming_url):
            update_data["douban_url"] = incoming_url
        return update_data if len(update_data) > 1 else None

    def _should_update_score(self, current: object, incoming: str) -> bool:
        current_text = str(current or "").strip()
        incoming_text = str(incoming or "").strip()
        if not incoming_text:
            return False
        if incoming_text == "无豆瓣评分" and current_text and current_text != "无豆瓣评分":
            return False
        return current_text != incoming_text

    def _should_update_url(self, current: object, incoming: str | None) -> bool:
        current_text = str(current or "").strip()
        incoming_text = str(incoming or "").strip()
        if not incoming_text and current_text:
            return False
        return current_text != incoming_text

    def _search_movies(self, title: str, page: int = 1) -> list[_DoubanSearchItem]:
        normalized_title = title.strip()
        if not normalized_title:
            return []
        url = self.base_url
        for attempt in range(1, _MAX_SEARCH_ATTEMPTS + 1):
            try:
                response = self.session.get(
                    url, params={"query": normalized_title},
                    headers=_DOUBAN_REQUEST_HEADERS, timeout=self.timeout,
                )
            except Exception as error:
                logger.error(
                    "Douban mobile search request failed: title=%s, url=%s, attempt=%s, error=%s",
                    normalized_title, url, attempt, error, exc_info=True,
                )
                continue
            if not response.ok:
                logger.error(
                    "Douban mobile search returned non-200: title=%s, status=%s, attempt=%s",
                    normalized_title, response.status_code, attempt,
                )
                continue
            return self._parse_search_html(response.text)
        logger.warning("Douban mobile search failed after retries: title=%s, page=%s", normalized_title, page)
        return []

    def _parse_search_html(self, html_content: str) -> list[_DoubanSearchItem]:
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            movie_module = self._find_movie_module(soup)
            if movie_module is None:
                return []
            candidates: list[_DoubanSearchItem] = []
            for link in movie_module.select("ul.search_results_subjects > li > a"):
                candidate = self._build_search_item_from_link(link)
                if candidate is not None:
                    candidates.append(candidate)
            return candidates
        except Exception as error:
            logger.error("Douban mobile search HTML parse failed: %s", error, exc_info=True)
            return []

    def _find_movie_module(self, soup: BeautifulSoup) -> Tag | None:
        for module in soup.select("li.search-module"):
            name_element = module.select_one(".search-results-modules-name")
            module_name = name_element.get_text(strip=True) if name_element is not None else ""
            if module_name == "电影":
                return module
        return None

    def _build_search_item_from_link(self, link: Tag) -> _DoubanSearchItem | None:
        href = link.get("href")
        if not isinstance(href, str):
            return None
        douban_url = self._normalize_subject_url(href)
        if douban_url is None:
            return None
        title_element = link.select_one("span.subject-title")
        title = title_element.get_text(strip=True) if title_element is not None else ""
        if not title:
            return None
        return _DoubanSearchItem(
            title=title,
            rating=self._extract_rating(link),
            cover_link=douban_url,
            year="", country="", actors=[],
        )

    def _normalize_subject_url(self, href: str) -> str | None:
        absolute_url = urljoin(_DOUBAN_MOBILE_BASE_URL, href)
        match = re.search(r"/movie/subject/(\d+)/?", absolute_url)
        if match is None:
            return None
        return f"{_DOUBAN_MOBILE_BASE_URL}/movie/subject/{match.group(1)}/"

    def _extract_rating(self, link: Tag) -> str:
        rating_element = link.select_one("p.rating")
        if rating_element is None:
            return ""
        rating_text = rating_element.get_text(" ", strip=True)
        match = re.search(r"\d+(?:\.\d+)?", rating_text)
        return match.group(0) if match is not None else ""

    # ---------- 内部: 匹配评分 ----------

    def _choose_best_candidate(
        self,
        movie: SupportsDoubanMatchingMovie,
        candidates: list[_DoubanSearchItem],
    ) -> _DoubanSearchItem | None:
        best: _DoubanSearchItem | None = None
        best_score = -1
        for candidate in candidates:
            score = self._calculate_match_score(movie, candidate)
            if score > best_score:
                best_score = score
                best = candidate
        return best if best_score >= 50 else None

    def _calculate_match_score(
        self,
        movie: SupportsDoubanMatchingMovie,
        candidate: _DoubanSearchItem,
    ) -> int:
        movie_title = self._normalize_text(movie.title or "")
        candidate_title = self._normalize_text(candidate.title)
        if not movie_title or not candidate_title:
            return 0

        score = 0
        if movie_title == candidate_title:
            score += 80
        elif movie_title in candidate_title or candidate_title in movie_title:
            score += 70

        movie_year = self._extract_year(movie.release_date)
        candidate_year = self._extract_year(candidate.year)
        if movie_year and candidate_year:
            if movie_year == candidate_year:
                score += 20
            else:
                score -= min(abs(movie_year - candidate_year) * 5, 20)

        movie_actor_names = self._split_people(movie.actors)
        if movie_actor_names and candidate.actors:
            overlap = len(set(movie_actor_names) & set(candidate.actors))
            score += min(overlap * 5, 15)
        return score

    def _extract_year(self, value: str | None) -> int | None:
        if not value:
            return None
        match = re.search(r"(\d{4})", value)
        return int(match.group(1)) if match is not None else None

    def _normalize_text(self, value: str) -> str:
        normalized = value.strip().lower()
        return re.sub(r"[\s:：·•\-—'\"《》\(\)（）\[\]【】,，.。!！?？/\\\\]+", "", normalized)

    def _split_people(self, value: str | None) -> list[str]:
        if not value:
            return []
        parts = re.split(r"[/、,，\s]+", value)
        return [item.strip() for item in parts if item.strip()]


update_douban_service = UpdateDoubanService()
