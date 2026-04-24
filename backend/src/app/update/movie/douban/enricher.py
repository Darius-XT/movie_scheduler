"""豆瓣评分与详情链接补充器。"""

from __future__ import annotations

import re
from typing import Protocol

from app.core.logger import logger
from app.update.movie.douban.client import DoubanApiClient, douban_api_client
from app.update.movie.douban.entities import DoubanMovieSearchItem, DoubanMovieSupplement


class SupportsDoubanMatchingMovie(Protocol):
    """支持豆瓣匹配所需字段的电影视图。"""

    @property
    def title(self) -> str | None: ...

    @property
    def release_date(self) -> str | None: ...

    @property
    def actors(self) -> str | None: ...


class DoubanInfoEnricher:
    """根据电影标题为电影补充豆瓣评分与详情链接。"""

    def __init__(self, client: DoubanApiClient | None = None) -> None:
        self.client = client or douban_api_client

    def fetch_movie_supplement(self, movie: SupportsDoubanMatchingMovie) -> DoubanMovieSupplement:
        """查询豆瓣候选并返回最佳匹配结果。"""
        title = (movie.title or "").strip()
        if not title:
            return DoubanMovieSupplement(score="无豆瓣评分", douban_url=None)

        candidates = self.client.search_movies(title=title, page=1)
        if not candidates:
            logger.debug("豆瓣搜索无结果: %s", title)
            return DoubanMovieSupplement(score="无豆瓣评分", douban_url=None)

        best_candidate = self._choose_best_candidate(movie, candidates)
        if best_candidate is None:
            logger.debug("豆瓣搜索未找到可信匹配: %s", title)
            return DoubanMovieSupplement(score="无豆瓣评分", douban_url=None)

        return DoubanMovieSupplement(
            score=best_candidate.rating or "无豆瓣评分",
            douban_url=best_candidate.cover_link,
        )

    def _choose_best_candidate(
        self,
        movie: SupportsDoubanMatchingMovie,
        candidates: list[DoubanMovieSearchItem],
    ) -> DoubanMovieSearchItem | None:
        best_candidate: DoubanMovieSearchItem | None = None
        best_score = -1

        for candidate in candidates:
            score = self._calculate_match_score(movie, candidate)
            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_score < 50:
            return None
        return best_candidate

    def _calculate_match_score(
        self,
        movie: SupportsDoubanMatchingMovie,
        candidate: DoubanMovieSearchItem,
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
            overlap_count = len(set(movie_actor_names) & set(candidate.actors))
            score += min(overlap_count * 5, 15)

        return score

    def _extract_year(self, value: str | None) -> int | None:
        if not value:
            return None
        match = re.search(r"(\d{4})", value)
        if match is None:
            return None
        return int(match.group(1))

    def _normalize_text(self, value: str) -> str:
        normalized = value.strip().lower()
        return re.sub(r"[\s:：·•\-—'\"《》\(\)（）\[\]【】,，.。!！?？/\\\\]+", "", normalized)

    def _split_people(self, value: str | None) -> list[str]:
        if not value:
            return []
        parts = re.split(r"[/、,，\s]+", value)
        return [item.strip() for item in parts if item.strip()]


douban_info_enricher = DoubanInfoEnricher()
