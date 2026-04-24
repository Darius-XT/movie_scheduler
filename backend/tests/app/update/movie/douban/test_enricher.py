"""豆瓣补充信息测试。"""

from __future__ import annotations

from typing import cast

from app.update.movie.base.entities import ScrapedMovieBaseInfo
from app.update.movie.douban.client import DoubanApiClient
from app.update.movie.douban.enricher import DoubanInfoEnricher
from app.update.movie.douban.entities import DoubanMovieSearchItem


class FakeDoubanApiClient:
    """用于测试的豆瓣 API 客户端。"""

    def __init__(self, results: list[DoubanMovieSearchItem]) -> None:
        self._results = results

    def search_movies(self, title: str, page: int = 1) -> list[DoubanMovieSearchItem]:
        del title, page
        return self._results


def _make_movie(title: str = "哪吒之魔童闹海", release_date: str = "2025-01-29") -> ScrapedMovieBaseInfo:
    return ScrapedMovieBaseInfo(id=1, title=title, genres="动画", actors="吕艳婷", release_date=release_date)


def test_douban_info_enricher_prefers_title_and_year_match() -> None:
    """应优先命中标题和年份都匹配的豆瓣候选。"""
    client = FakeDoubanApiClient([
        DoubanMovieSearchItem(title="哪吒之魔童降世", rating="8.4",
                              cover_link="https://movie.douban.com/subject/26794435/",
                              year="2019", country="中国大陆", actors=["饺子", "吕艳婷"]),
        DoubanMovieSearchItem(title="哪吒之魔童闹海", rating="8.4",
                              cover_link="https://movie.douban.com/subject/34780991/",
                              year="2025", country="中国大陆", actors=["饺子", "吕艳婷"]),
    ])
    enricher = DoubanInfoEnricher(client=cast(DoubanApiClient, client))

    result = enricher.fetch_movie_supplement(_make_movie())

    assert result.score == "8.4"
    assert result.douban_url == "https://movie.douban.com/subject/34780991/"


def test_douban_info_enricher_returns_no_score_when_title_is_empty() -> None:
    """标题为空时应返回无豆瓣评分且无链接。"""
    enricher = DoubanInfoEnricher(client=cast(DoubanApiClient, FakeDoubanApiClient([])))

    result = enricher.fetch_movie_supplement(_make_movie(title=""))

    assert result.score == "无豆瓣评分"
    assert result.douban_url is None


def test_douban_info_enricher_returns_no_score_when_no_candidates() -> None:
    """搜索无结果时应返回无豆瓣评分且无链接。"""
    enricher = DoubanInfoEnricher(client=cast(DoubanApiClient, FakeDoubanApiClient([])))

    result = enricher.fetch_movie_supplement(_make_movie())

    assert result.score == "无豆瓣评分"
    assert result.douban_url is None


def test_douban_info_enricher_returns_no_score_when_no_confident_match() -> None:
    """候选列表存在但与目标电影相似度不足时，应返回无豆瓣评分且无链接。"""
    client = FakeDoubanApiClient([
        DoubanMovieSearchItem(title="完全不同的电影", rating="7.0",
                              cover_link="https://movie.douban.com/subject/99999/",
                              year="1990", country="美国", actors=["某人"]),
    ])
    enricher = DoubanInfoEnricher(client=cast(DoubanApiClient, client))

    result = enricher.fetch_movie_supplement(_make_movie())

    assert result.score == "无豆瓣评分"
    assert result.douban_url is None
