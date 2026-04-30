"""电影基础信息更新器。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import cast

from app.core.logger import logger
from app.models.movie import MovieWriteData
from app.repositories.movie import movie_repository
from app.update.entities import UpdateProgressEvent
from app.update.movie.base.client import MovieBaseInfoClient
from app.update.movie.base.entities import (
    MovieBaseInfoInputStats,
    MovieBaseInfoResultStats,
    MovieBaseInfoUpdateStats,
    ScrapedMovieBaseInfo,
)

_BEIJING_TZ = timezone(timedelta(hours=8))


def _now_beijing_datetime() -> datetime:
    """返回北京时间的 datetime（秒级精度，与 DB server_default 对齐）。"""
    return datetime.now(_BEIJING_TZ).replace(tzinfo=None, microsecond=0)


class MovieBaseInfoUpdater:
    """负责抓取电影列表并执行增量更新。"""

    def __init__(self) -> None:
        self.client = MovieBaseInfoClient()

    def update_all_movie_base_info(
        self,
        city_id: int,
        progress_callback: Callable[[UpdateProgressEvent], None] | None = None,
    ) -> MovieBaseInfoUpdateStats:
        """更新电影基础信息。"""
        logger.info("开始更新电影基础信息，city_id=%s", city_id)
        if progress_callback is not None:
            progress_callback(
                UpdateProgressEvent(message="正在抓取电影列表", stage="fetching_movie_list", city_id=city_id)
            )

        existing_movie_ids = {cast(int, m.id) for m in movie_repository.get_all_movies()}
        logger.debug("数据库当前有 %s 部电影", len(existing_movie_ids))

        all_scraped_movies, showing_movie_ids = self._scrape_all_movies(city_id, progress_callback)
        for movie in all_scraped_movies:
            movie.is_showing = movie.id in showing_movie_ids

        input_stats = self._build_input_stats(all_scraped_movies, showing_movie_ids)
        result_stats = self._perform_incremental_update(existing_movie_ids, all_scraped_movies)
        stats = MovieBaseInfoUpdateStats(input_stats=input_stats, result_stats=result_stats)

        self._log_stats(stats)
        if progress_callback is not None:
            progress_callback(
                UpdateProgressEvent(
                    message=(
                        f"基础信息更新完成：新增 {stats.result_stats.added} 部，"
                        f"更新 {stats.result_stats.updated} 部，删除 {stats.result_stats.removed} 部"
                    ),
                    stage="base_info_completed",
                    current=stats.input_stats.deduplicated_total,
                    total=stats.input_stats.deduplicated_total,
                    city_id=city_id,
                )
            )
        return stats

    def _scrape_all_movies(
        self,
        city_id: int,
        progress_callback: Callable[[UpdateProgressEvent], None] | None,
    ) -> tuple[list[ScrapedMovieBaseInfo], set[int]]:
        """抓取正在热映和即将上映的所有电影。"""
        all_scraped_movies: list[ScrapedMovieBaseInfo] = []
        showing_movie_ids: set[int] = set()

        for show_type in range(1, 3):
            show_type_name = "正在热映" if show_type == 1 else "即将上映"
            type_movies = self._scrape_one_type(show_type, show_type_name, city_id, progress_callback)
            if show_type == 1:
                showing_movie_ids = {m.id for m in type_movies}
            all_scraped_movies.extend(type_movies)

        return all_scraped_movies, showing_movie_ids

    def _scrape_one_type(
        self,
        show_type: int,
        show_type_name: str,
        city_id: int,
        progress_callback: Callable[[UpdateProgressEvent], None] | None,
    ) -> list[ScrapedMovieBaseInfo]:
        """抓取单个类型（热映或即将上映）的所有分页电影。"""
        logger.debug("开始抓取 %s 电影", show_type_name)
        type_movies: list[ScrapedMovieBaseInfo] = []
        page = 1
        while True:
            if progress_callback is not None:
                progress_callback(
                    UpdateProgressEvent(
                        message=f"正在抓取{show_type_name}第 {page} 页",
                        stage="fetching_movie_list",
                        city_id=city_id,
                        page=page,
                    )
                )
            result = self.client.fetch_page(show_type, page, city_id)
            if result is None:
                logger.warning("获取页面失败，跳过 page=%s", page)
                break
            movies_data, is_expected_empty = result
            if is_expected_empty:
                logger.debug("%s 抓取完成，共 %s 页", show_type_name, page - 1)
                break
            if not movies_data:
                logger.error("第 %s 页未解析到电影数据，结束抓取", page)
                break
            type_movies.extend(movies_data)
            logger.debug("第 %s 页解析到 %s 部电影", page, len(movies_data))
            page += 1
        logger.info("%s 列表抓取完成，共抓取 %s 部电影", show_type_name, len(type_movies))
        return type_movies

    def _log_stats(self, stats: MovieBaseInfoUpdateStats) -> None:
        """输出更新统计日志。"""
        logger.info(
            "基础电影信息输入统计: 抓取总数=%d, 正在热映=%d, 即将上映=%d, 重复=%d, 去重后总数=%d",
            stats.input_stats.scraped_total,
            stats.input_stats.showing,
            stats.input_stats.upcoming,
            stats.input_stats.duplicate,
            stats.input_stats.deduplicated_total,
        )
        logger.info(
            "基础电影信息更新结果统计: 原有=%d, 新增=%d, 更新=%d, 删除=%d, 当前总数=%d",
            stats.result_stats.existing,
            stats.result_stats.added,
            stats.result_stats.updated,
            stats.result_stats.removed,
            stats.result_stats.total,
        )

    def _build_input_stats(
        self,
        scraped_movies: list[ScrapedMovieBaseInfo],
        showing_movie_ids: set[int],
    ) -> MovieBaseInfoInputStats:
        """统计抓取输入结果。"""
        scraped_total = len(scraped_movies)
        scraped_ids = [movie.id for movie in scraped_movies]
        deduplicated_total = len(set(scraped_ids))
        upcoming_count = sum(1 for mid in set(scraped_ids) if mid not in showing_movie_ids)
        return MovieBaseInfoInputStats(
            scraped_total=scraped_total,
            showing=len(showing_movie_ids),
            upcoming=upcoming_count,
            duplicate=scraped_total - deduplicated_total,
            deduplicated_total=deduplicated_total,
        )

    def _perform_incremental_update(
        self,
        existing_movie_ids: set[int],
        scraped_movies: list[ScrapedMovieBaseInfo],
    ) -> MovieBaseInfoResultStats:
        """执行增量更新并返回更新结果统计。"""
        unique_scraped_movies = self._deduplicate_scraped_movies(scraped_movies)
        scraped_movie_ids = {movie.id for movie in unique_scraped_movies}
        added_movie_ids = scraped_movie_ids - existing_movie_ids
        removed_movie_ids = existing_movie_ids - scraped_movie_ids
        existing_but_updated_ids = scraped_movie_ids & existing_movie_ids

        return MovieBaseInfoResultStats(
            existing=len(existing_movie_ids),
            added=self._add_new_movies(unique_scraped_movies, added_movie_ids),
            added_movie_ids=sorted(added_movie_ids),
            updated=self._update_existing_movies(unique_scraped_movies, existing_but_updated_ids),
            updated_movie_ids=sorted(existing_but_updated_ids),
            removed=self._remove_stale_movies(removed_movie_ids),
            total=movie_repository.get_movies_count(),
        )

    def _add_new_movies(
        self,
        unique_scraped_movies: list[ScrapedMovieBaseInfo],
        added_movie_ids: set[int],
    ) -> int:
        """保存新增电影，返回成功数量。"""
        count = 0
        for movie in unique_scraped_movies:
            if movie.id not in added_movie_ids:
                continue
            data = asdict(movie)
            if movie.is_showing:
                data["first_showing_at"] = _now_beijing_datetime()
            if movie_repository.save_movie(cast(MovieWriteData, data)):
                count += 1
                logger.info("添加新电影 %s (ID: %s)", movie.title, movie.id)
        return count

    def _update_existing_movies(
        self,
        unique_scraped_movies: list[ScrapedMovieBaseInfo],
        existing_but_updated_ids: set[int],
    ) -> int:
        """更新已有电影基础信息，返回成功数量。"""
        count = 0
        for movie in unique_scraped_movies:
            if movie.id not in existing_but_updated_ids:
                continue
            existing_movie = movie_repository.get_movie_by_id(movie.id)
            if existing_movie is None:
                continue
            existing_is_showing = cast(bool, existing_movie.is_showing)
            update_data: MovieWriteData = {
                "id": movie.id,
                "is_showing": movie.is_showing,
                "title": movie.title,
                "genres": movie.genres,
                "actors": movie.actors,
                "release_date": movie.release_date,
            }
            if not existing_is_showing and movie.is_showing:
                update_data["first_showing_at"] = _now_beijing_datetime()
            if movie_repository.save_movie(update_data):
                count += 1
                if existing_is_showing != movie.is_showing:
                    logger.info(
                        "更新电影状态 %s (ID: %s), is_showing: %s -> %s",
                        movie.title or "Unknown",
                        movie.id,
                        existing_is_showing,
                        movie.is_showing,
                    )
                else:
                    logger.debug("更新电影基础信息: %s (ID: %s)", movie.title or "Unknown", movie.id)
        return count

    def _remove_stale_movies(self, removed_movie_ids: set[int]) -> int:
        """删除下架电影，返回成功数量。"""
        count = 0
        for movie_id in removed_movie_ids:
            movie = movie_repository.get_movie_by_id(movie_id)
            if movie is not None and movie_repository.delete_movie(movie_id):
                count += 1
                logger.info("删除下架电影: %s (ID: %s)", movie.title, movie_id)
        return count

    def _deduplicate_scraped_movies(
        self,
        scraped_movies: list[ScrapedMovieBaseInfo],
    ) -> list[ScrapedMovieBaseInfo]:
        """按电影 ID 去重，确保更新统计以唯一电影为单位。"""
        seen: dict[int, ScrapedMovieBaseInfo] = {}
        for movie in scraped_movies:
            seen[movie.id] = movie
        return list(seen.values())


movie_base_info_updater = MovieBaseInfoUpdater()
