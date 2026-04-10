"""豆瓣补充信息测试。"""

from __future__ import annotations

from typing import cast

from app.use_cases.update.movie_info.base_info.models import ScrapedMovieBaseInfo
from app.use_cases.update.movie_info.douban.douban_api_client import DoubanApiClient
from app.use_cases.update.movie_info.douban.douban_info_enricher import DoubanInfoEnricher
from app.use_cases.update.movie_info.douban.models import DoubanMovieSearchItem


class FakeDoubanApiClient:
    """用于测试的豆瓣 API 客户端。"""

    def search_movies(self, title: str, page: int = 1) -> list[DoubanMovieSearchItem]:
        assert title == "哪吒之魔童闹海"
        assert page == 1
        return [
            DoubanMovieSearchItem(
                title="哪吒之魔童降世",
                rating="8.4",
                cover_link="https://movie.douban.com/subject/26794435/",
                year="2019",
                country="中国大陆",
                actors=["饺子", "吕艳婷"],
            ),
            DoubanMovieSearchItem(
                title="哪吒之魔童闹海",
                rating="8.4",
                cover_link="https://movie.douban.com/subject/34780991/",
                year="2025",
                country="中国大陆",
                actors=["饺子", "吕艳婷"],
            ),
        ]


def test_douban_info_enricher_prefers_title_and_year_match() -> None:
    """应优先命中标题和年份都匹配的豆瓣候选。"""
    enricher = DoubanInfoEnricher(client=cast(DoubanApiClient, FakeDoubanApiClient()))
    movie = ScrapedMovieBaseInfo(
        id=1,
        title="哪吒之魔童闹海",
        genres="动画",
        actors="吕艳婷",
        release_date="2025-01-29",
    )

    result = enricher.fetch_movie_supplement(movie)

    assert result.score == "8.4"
    assert result.douban_url == "https://movie.douban.com/subject/34780991/"
