"""更新流程测试。"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import cast

import pytest

from app.models.movie import MovieWriteData
from app.repositories.movie import movie_repository
from app.services.update.cinema.updater import CinemaInfoUpdater
from app.services.update.entities import UpdateProgressEvent
from app.services.update.movie.base.entities import (
    MovieBaseInfoInputStats,
    MovieBaseInfoResultStats,
    MovieBaseInfoUpdateStats,
    ScrapedMovieBaseInfo,
)
from app.services.update.movie.base.updater import MovieBaseInfoUpdater
from app.services.update.movie.extra.updater import MovieExtraInfoUpdater
from app.services.update.movie.updater import MovieInfoUpdater
from app.services.update.movie_update_reset_helper import MovieUpdateResetHelper
from app.services.update.result_builder import (
    UpdateMovieBaseInfoResult,
    UpdateMovieExtraInfoResult,
    UpdateMovieInputStatsResult,
    UpdateMovieResult,
    UpdateMovieResultStatsResult,
    UpdateResultBuilder,
)
from app.services.update.updater import InfoUpdateUseCase

UpdateProgressCallback = Callable[[UpdateProgressEvent], None]


class FakeResetHelper:
    """用于测试的重置辅助类。"""

    def __init__(self) -> None:
        self.called_with: list[bool] = []

    def reset_movies_if_needed(self, force_update_all: bool) -> None:
        self.called_with.append(force_update_all)


class FakeBaseInfoUpdater:
    """用于测试的基础信息更新器。"""

    def update_all_movie_base_info(
        self,
        city_id: int,
        progress_callback: UpdateProgressCallback | None = None,
    ) -> MovieBaseInfoUpdateStats:
        assert city_id == 10
        assert progress_callback is None
        return MovieBaseInfoUpdateStats(
            input_stats=MovieBaseInfoInputStats(
                scraped_total=12,
                showing=5,
                upcoming=6,
                duplicate=1,
                deduplicated_total=11,
            ),
            result_stats=MovieBaseInfoResultStats(
                existing=9,
                added=2,
                added_movie_ids=[101, 102],
                updated=3,
                updated_movie_ids=[1, 2, 3],
                removed=1,
                total=10,
            ),
        )


class FakeExtraInfoUpdater:
    """用于测试的额外信息更新器。"""

    async def update_all_movie_extra_info(
        self,
        force_update_all: bool = False,
        progress_callback: UpdateProgressCallback | None = None,
    ) -> int:
        assert force_update_all is True
        assert progress_callback is None
        return 3


class FakeMovieInfoUpdater:
    """用于测试的电影更新器。"""

    async def update_all_movie_info(
        self,
        city_id: int,
        force_update_all: bool,
        progress_callback: UpdateProgressCallback | None = None,
    ) -> UpdateMovieResult:
        assert city_id == 10
        assert force_update_all is True
        assert progress_callback is None
        return UpdateMovieResult(
            base_info=UpdateMovieBaseInfoResult(
                input_stats=UpdateMovieInputStatsResult(
                    scraped_total=6,
                    showing=2,
                    upcoming=3,
                    duplicate=1,
                    deduplicated_total=5,
                ),
                result_stats=UpdateMovieResultStatsResult(
                    existing=4,
                    added=1,
                    added_movie_ids=[501],
                    updated=2,
                    updated_movie_ids=[11, 12],
                    removed=0,
                    total=5,
                ),
            ),
            extra_info=UpdateMovieExtraInfoResult(updated_count=2),
        )


class FakeCinemaInfoUpdater:
    """用于测试的影院更新器。"""

    def update_all_cinema_info(
        self,
        city_id: int,
        force_update_all: bool = False,
        progress_callback: UpdateProgressCallback | None = None,
    ) -> tuple[int, int]:
        assert city_id == 10
        assert progress_callback is None
        return 5, 1


@dataclass
class FakeExistingMovie:
    id: int
    title: str
    is_showing: bool


def test_base_info_updater_counts_updated_by_unique_movie_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """基础信息更新统计中的更新数应按唯一电影 ID 计算。"""

    updater = MovieBaseInfoUpdater()
    scraped_movies = [
        ScrapedMovieBaseInfo(
            id=1,
            title="电影1",
            genres="剧情",
            actors="演员A",
            release_date="2025-01-01",
            is_showing=True,
        ),
        ScrapedMovieBaseInfo(
            id=1,
            title="电影1",
            genres="剧情",
            actors="演员A",
            release_date="2025-01-01",
            is_showing=True,
        ),
    ]

    save_calls: list[int] = []

    def get_movie_by_id(movie_id: int) -> FakeExistingMovie:
        return FakeExistingMovie(id=movie_id, title="电影1", is_showing=False)

    def save_movie(movie_data: MovieWriteData) -> bool:
        save_calls.append(movie_data["id"])
        assert "score" not in movie_data
        assert "douban_url" not in movie_data
        return True

    monkeypatch.setattr(movie_repository, "get_movie_by_id", get_movie_by_id)
    monkeypatch.setattr(movie_repository, "save_movie", save_movie)
    monkeypatch.setattr(movie_repository, "get_movies_count", lambda: 1)

    result = updater._perform_incremental_update({1}, scraped_movies)  # pyright: ignore[reportPrivateUsage]

    assert result.updated == 1
    assert save_calls == [1]


def test_all_movie_info_updater_orchestrates_full_flow() -> None:
    """电影更新器应串联重置、基础信息和额外信息更新。"""
    reset_helper = FakeResetHelper()
    updater = MovieInfoUpdater(
        reset_helper=cast(MovieUpdateResetHelper, reset_helper),
        result_builder=UpdateResultBuilder(),
    )
    updater.base_info_updater = cast(MovieBaseInfoUpdater, FakeBaseInfoUpdater())
    updater.extra_info_updater = cast(MovieExtraInfoUpdater, FakeExtraInfoUpdater())

    result = asyncio.run(updater.update_all_movie_info(city_id=10, force_update_all=True))

    assert reset_helper.called_with == [True]
    assert asdict(result) == {
        "base_info": {
            "input_stats": {
                "scraped_total": 12,
                "showing": 5,
                "upcoming": 6,
                "duplicate": 1,
                "deduplicated_total": 11,
            },
            "result_stats": {
                "existing": 9,
                "added": 2,
                "added_movie_ids": [101, 102],
                "updated": 3,
                "updated_movie_ids": [1, 2, 3],
                "removed": 1,
                "total": 10,
            },
        },
        "extra_info": {"updated_count": 3},
    }


def test_info_update_use_case_orchestrates_cinema_result_building() -> None:
    """信息更新用例入口应把影院更新结果转换为标准结构。"""
    use_case = InfoUpdateUseCase(result_builder=UpdateResultBuilder())
    use_case.movie_info_updater = cast(MovieInfoUpdater, FakeMovieInfoUpdater())
    use_case.cinema_info_updater = cast(CinemaInfoUpdater, FakeCinemaInfoUpdater())

    movie_result = asyncio.run(use_case.update_movie_info(city_id=10, force_update_all=True))
    cinema_result = use_case.update_cinema_info(city_id=10)

    assert asdict(movie_result) == {
        "base_info": {
            "input_stats": {
                "scraped_total": 6,
                "showing": 2,
                "upcoming": 3,
                "duplicate": 1,
                "deduplicated_total": 5,
            },
            "result_stats": {
                "existing": 4,
                "added": 1,
                "added_movie_ids": [501],
                "updated": 2,
                "updated_movie_ids": [11, 12],
                "removed": 0,
                "total": 5,
            },
        },
        "extra_info": {"updated_count": 2},
    }
    assert asdict(cinema_result) == {"success_count": 5, "failure_count": 1}
