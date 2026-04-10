"""电影基础信息更新器。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import cast

from app.core.logger import logger
from app.models.movie import MovieWriteData
from app.repositories.movie_repository import movie_repository
from app.use_cases.update.models import UpdateProgressEvent
from app.use_cases.update.movie_info.base_info.base_info_parser import MovieBaseInfoParser
from app.use_cases.update.movie_info.base_info.base_info_scraper import MovieBaseInfoScraper
from app.use_cases.update.movie_info.base_info.models import (
    MovieBaseInfoInputStats,
    MovieBaseInfoResultStats,
    MovieBaseInfoUpdateStats,
    ScrapedMovieBaseInfo,
)


class MovieBaseInfoUpdater:
    """负责抓取电影列表并执行增量更新。"""

    def __init__(self) -> None:
        self.parser = MovieBaseInfoParser()
        self.scraper = MovieBaseInfoScraper()

    def update_all_movie_base_info(
        self,
        city_id: int,
        progress_callback: Callable[[UpdateProgressEvent], None] | None = None,
    ) -> MovieBaseInfoUpdateStats:
        """更新电影基础信息。"""
        logger.info("开始更新电影基础信息，city_id=%s", city_id)
        if progress_callback is not None:
            progress_callback(
                UpdateProgressEvent(
                    message="正在抓取电影列表",
                    stage="fetching_movie_list",
                    city_id=city_id,
                )
            )

        existing_movies = movie_repository.get_all_movies()
        existing_movie_ids = {cast(int, movie.id) for movie in existing_movies}
        logger.debug("数据库当前有 %s 部电影", len(existing_movie_ids))

        all_scraped_movies: list[ScrapedMovieBaseInfo] = []
        showing_movie_ids: set[int] = set()

        for show_type in range(1, 3):
            show_type_name = "正在热映" if show_type == 1 else "即将上映"
            logger.debug("开始抓取 %s 电影", show_type_name)
            if progress_callback is not None:
                progress_callback(
                    UpdateProgressEvent(
                        message=f"开始抓取{show_type_name}电影列表",
                        stage="fetching_movie_list",
                        city_id=city_id,
                    )
                )

            page = 1
            type_movies: list[ScrapedMovieBaseInfo] = []
            while True:
                logger.debug("抓取 %s 第 %s 页", show_type_name, page)
                if progress_callback is not None:
                    progress_callback(
                        UpdateProgressEvent(
                            message=f"正在抓取{show_type_name}第 {page} 页",
                            stage="fetching_movie_list",
                            city_id=city_id,
                            page=page,
                        )
                    )
                success, html_content = self.scraper.scrape_movies(show_type, page, city_id)
                if not success or not html_content:
                    logger.warning("获取页面失败，跳过 page=%s", page)
                    break

                movies_data, is_expected_empty = self.parser.parse_movies(html_content)
                if is_expected_empty:
                    logger.debug("%s 抓取完成，共 %s 页", show_type_name, page - 1)
                    break
                if not movies_data:
                    logger.error("第 %s 页未解析到电影数据，结束抓取", page)
                    break

                if show_type == 1:
                    for movie in movies_data:
                        showing_movie_ids.add(movie.id)

                type_movies.extend(movies_data)
                logger.debug("第 %s 页解析到 %s 部电影", page, len(movies_data))
                page += 1

            logger.info("%s 列表抓取完成，共抓取 %s 部电影", show_type_name, len(type_movies))
            if progress_callback is not None:
                progress_callback(
                    UpdateProgressEvent(
                        message=f"{show_type_name}列表抓取完成，共 {len(type_movies)} 部电影",
                        stage="fetching_movie_list",
                        city_id=city_id,
                    )
                )
            all_scraped_movies.extend(type_movies)

        for movie in all_scraped_movies:
            movie.is_showing = movie.id in showing_movie_ids

        input_stats = self._build_input_stats(all_scraped_movies, showing_movie_ids)
        result_stats = self._perform_incremental_update(existing_movie_ids, all_scraped_movies)
        stats = MovieBaseInfoUpdateStats(
            input_stats=input_stats,
            result_stats=result_stats,
        )

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

    def _build_input_stats(
        self,
        scraped_movies: list[ScrapedMovieBaseInfo],
        showing_movie_ids: set[int],
    ) -> MovieBaseInfoInputStats:
        """统计抓取输入结果。"""
        scraped_total = len(scraped_movies)
        scraped_ids = [movie.id for movie in scraped_movies]
        deduplicated_total = len(set(scraped_ids))
        duplicate_count = scraped_total - deduplicated_total
        upcoming_count = sum(1 for movie_id in set(scraped_ids) if movie_id not in showing_movie_ids)
        return MovieBaseInfoInputStats(
            scraped_total=scraped_total,
            showing=len(showing_movie_ids),
            upcoming=upcoming_count,
            duplicate=duplicate_count,
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

        added_count = 0
        for movie in unique_scraped_movies:
            if movie.id in added_movie_ids and movie_repository.save_movie(cast(MovieWriteData, asdict(movie))):
                added_count += 1
                logger.info("添加新电影 %s (ID: %s)", movie.title, movie.id)

        updated_count = 0
        for movie in unique_scraped_movies:
            if movie.id not in existing_but_updated_ids:
                continue

            existing_movie = movie_repository.get_movie_by_id(movie.id)
            if existing_movie is None:
                continue

            existing_movie_is_showing = cast(bool, existing_movie.is_showing)
            update_data: MovieWriteData = {
                "id": movie.id,
                "is_showing": movie.is_showing,
                "title": movie.title,
                "genres": movie.genres,
                "actors": movie.actors,
                "release_date": movie.release_date,
            }
            if movie_repository.save_movie(update_data):
                updated_count += 1
                if existing_movie_is_showing != movie.is_showing:
                    logger.info(
                        "更新电影状态 %s (ID: %s), is_showing: %s -> %s",
                        movie.title or "Unknown",
                        movie.id,
                        existing_movie_is_showing,
                        movie.is_showing,
                    )
                else:
                    logger.debug("更新电影基础信息: %s (ID: %s)", movie.title or "Unknown", movie.id)

        removed_count = 0
        for movie_id in removed_movie_ids:
            movie = movie_repository.get_movie_by_id(movie_id)
            if movie is not None and movie_repository.delete_movie(movie_id):
                removed_count += 1
                logger.info("删除下架电影: %s (ID: %s)", movie.title, movie_id)

        return MovieBaseInfoResultStats(
            existing=len(existing_movie_ids),
            added=added_count,
            added_movie_ids=sorted(added_movie_ids),
            updated=updated_count,
            updated_movie_ids=sorted(existing_but_updated_ids),
            removed=removed_count,
            total=movie_repository.get_movies_count(),
        )

    def _deduplicate_scraped_movies(
        self,
        scraped_movies: list[ScrapedMovieBaseInfo],
    ) -> list[ScrapedMovieBaseInfo]:
        """按电影 ID 去重，确保更新统计以唯一电影为单位。"""
        deduplicated_movies: dict[int, ScrapedMovieBaseInfo] = {}
        for movie in scraped_movies:
            deduplicated_movies[movie.id] = movie
        return list(deduplicated_movies.values())


movie_base_info_updater = MovieBaseInfoUpdater()
