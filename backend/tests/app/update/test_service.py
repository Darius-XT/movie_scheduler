"""更新服务测试。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pytest

from app.core.exceptions import AppError
from app.models.movie import Movie, MovieWriteData
from app.update.movie.douban.enricher import DoubanInfoEnricher, SupportsDoubanMatchingMovie
from app.update.movie.douban.entities import DoubanMovieSupplement
from app.update.service import UpdateService, update_service


def test_update_service_accepts_known_city_id() -> None:
    """已配置的城市 ID 应通过校验。"""
    assert update_service._normalize_city_id(10) == 10  # pyright: ignore[reportPrivateUsage]


def test_update_service_rejects_unknown_city_id() -> None:
    """未配置的城市 ID 应被拒绝。"""
    with pytest.raises(AppError):
        update_service._normalize_city_id(999999)  # pyright: ignore[reportPrivateUsage]


# ── fetch_douban_for_movie ──────────────────────────────────────────────────


@dataclass
class FakeMovie:
    title: str | None = "闪灵"
    release_date: str | None = "2026-01-30"
    actors: str | None = "杰克·尼科尔森"


class FakeEnricher:
    def __init__(self, supplement: DoubanMovieSupplement) -> None:
        self._supplement = supplement

    def fetch_movie_supplement(self, movie: SupportsDoubanMatchingMovie) -> DoubanMovieSupplement:
        del movie
        return self._supplement


@pytest.mark.anyio
async def test_fetch_douban_raises_404_when_movie_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """电影不存在时应抛出 AppError 404。"""
    import app.repositories.movie as repo_module

    def fake_get_by_id(movie_id: int) -> Movie | None:
        del movie_id
        return None

    monkeypatch.setattr(repo_module.movie_repository, "get_movie_by_id", fake_get_by_id)
    service = UpdateService(enricher=cast(DoubanInfoEnricher, FakeEnricher(
        DoubanMovieSupplement(score="无豆瓣评分", douban_url=None)
    )))

    with pytest.raises(AppError) as exc_info:
        await service.fetch_douban_for_movie(99999)

    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_fetch_douban_returns_supplement_when_matched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """豆瓣匹配成功时应持久化并返回评分和链接。"""
    import app.repositories.movie as repo_module

    saved: list[MovieWriteData] = []

    def fake_get_by_id(movie_id: int) -> FakeMovie:
        del movie_id
        return FakeMovie()

    def fake_save(data: MovieWriteData) -> bool:
        saved.append(data)
        return True

    monkeypatch.setattr(repo_module.movie_repository, "get_movie_by_id", fake_get_by_id)
    monkeypatch.setattr(repo_module.movie_repository, "save_movie", fake_save)

    supplement = DoubanMovieSupplement(score="8.3", douban_url="https://movie.douban.com/subject/1292428/")
    service = UpdateService(enricher=cast(DoubanInfoEnricher, FakeEnricher(supplement)))

    result = await service.fetch_douban_for_movie(1323)

    assert result.score == "8.3"
    assert result.douban_url == "https://movie.douban.com/subject/1292428/"
    assert len(saved) == 1
    assert saved[0].get("score") == "8.3"


@pytest.mark.anyio
async def test_fetch_douban_returns_no_score_when_unmatched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """豆瓣无匹配时应持久化无豆瓣评分标记并返回。"""
    import app.repositories.movie as repo_module

    saved: list[MovieWriteData] = []

    def fake_get_by_id(movie_id: int) -> FakeMovie:
        del movie_id
        return FakeMovie()

    def fake_save(data: MovieWriteData) -> bool:
        saved.append(data)
        return True

    monkeypatch.setattr(repo_module.movie_repository, "get_movie_by_id", fake_get_by_id)
    monkeypatch.setattr(repo_module.movie_repository, "save_movie", fake_save)

    supplement = DoubanMovieSupplement(score="无豆瓣评分", douban_url=None)
    service = UpdateService(enricher=cast(DoubanInfoEnricher, FakeEnricher(supplement)))

    result = await service.fetch_douban_for_movie(1323)

    assert result.score == "无豆瓣评分"
    assert result.douban_url is None
    assert saved[0].get("score") == "无豆瓣评分"
