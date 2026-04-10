"""更新结果组装器。"""

from __future__ import annotations

from dataclasses import dataclass

from app.use_cases.update.movie_info.base_info.models import (
    MovieBaseInfoInputStats,
    MovieBaseInfoResultStats,
    MovieBaseInfoUpdateStats,
)


@dataclass(slots=True)
class UpdateMovieInputStatsResult:
    """电影基础信息抓取输入统计。"""

    scraped_total: int
    showing: int
    upcoming: int
    duplicate: int
    deduplicated_total: int


@dataclass(slots=True)
class UpdateMovieResultStatsResult:
    """电影基础信息更新结果统计。"""

    existing: int
    added: int
    added_movie_ids: list[int]
    updated: int
    updated_movie_ids: list[int]
    removed: int
    total: int


@dataclass(slots=True)
class UpdateMovieBaseInfoResult:
    """电影基础信息更新结果。"""

    input_stats: UpdateMovieInputStatsResult
    result_stats: UpdateMovieResultStatsResult


@dataclass(slots=True)
class UpdateMovieExtraInfoResult:
    """电影额外信息更新统计。"""

    updated_count: int


@dataclass(slots=True)
class UpdateMovieDoubanInfoResult:
    """电影豆瓣信息更新统计。"""

    updated_count: int


@dataclass(slots=True)
class UpdateMovieResult:
    """电影更新结果。"""

    base_info: UpdateMovieBaseInfoResult
    extra_info: UpdateMovieExtraInfoResult
    douban_info: UpdateMovieDoubanInfoResult


@dataclass(slots=True)
class UpdateCinemaResult:
    """影院更新结果。"""

    success_count: int
    failure_count: int


class UpdateResultBuilder:
    """负责组装 update 用例的返回结果。"""

    def build_movie_update_result(
        self,
        base_info_stats: MovieBaseInfoUpdateStats,
        extra_info_updated_count: int,
        douban_info_updated_count: int,
    ) -> UpdateMovieResult:
        """组装电影更新结果。"""
        return UpdateMovieResult(
            base_info=UpdateMovieBaseInfoResult(
                input_stats=self._build_movie_input_stats(base_info_stats.input_stats),
                result_stats=self._build_movie_result_stats(base_info_stats.result_stats),
            ),
            extra_info=UpdateMovieExtraInfoResult(updated_count=extra_info_updated_count),
            douban_info=UpdateMovieDoubanInfoResult(updated_count=douban_info_updated_count),
        )

    def build_cinema_update_result(
        self,
        success_count: int,
        failure_count: int,
    ) -> UpdateCinemaResult:
        """组装影院更新结果。"""
        return UpdateCinemaResult(
            success_count=success_count,
            failure_count=failure_count,
        )

    def _build_movie_input_stats(
        self,
        stats: MovieBaseInfoInputStats,
    ) -> UpdateMovieInputStatsResult:
        """组装电影基础信息抓取输入统计。"""
        return UpdateMovieInputStatsResult(
            scraped_total=stats.scraped_total,
            showing=stats.showing,
            upcoming=stats.upcoming,
            duplicate=stats.duplicate,
            deduplicated_total=stats.deduplicated_total,
        )

    def _build_movie_result_stats(
        self,
        stats: MovieBaseInfoResultStats,
    ) -> UpdateMovieResultStatsResult:
        """组装电影基础信息更新结果统计。"""
        return UpdateMovieResultStatsResult(
            existing=stats.existing,
            added=stats.added,
            added_movie_ids=stats.added_movie_ids,
            updated=stats.updated,
            updated_movie_ids=stats.updated_movie_ids,
            removed=stats.removed,
            total=stats.total,
        )


update_result_builder = UpdateResultBuilder()
