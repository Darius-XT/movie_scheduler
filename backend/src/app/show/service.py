"""场次业务服务。"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from app.core.config import config_manager
from app.core.exceptions import AppError, DataParsingError, ExternalDependencyError, RepositoryError
from app.core.logger import logger
from app.models.movie_show import MovieShowWriteData
from app.repositories.movie import movie_repository
from app.repositories.movie_show import movie_show_repository, show_fetch_run_repository
from app.show.fetcher import show_fetcher
from app.show.result_builder import FinalMovieShowData

_BEIJING_TZ = timezone(timedelta(hours=8))


def _now_beijing_datetime() -> datetime:
    """返回北京时间的 datetime(秒级精度,与 DB server_default 对齐)。"""
    return datetime.now(_BEIJING_TZ).replace(tzinfo=None, microsecond=0)


class ShowService:
    """聚合场次抓取与持久化能力。"""

    async def refresh_wished_movie_shows(self, city_id: int | None = None) -> int:
        """抓取所有想看电影的场次并写入数据库,返回成功电影数。

        - 启动时与每小时触发一次,由调度器调用;不抛异常,失败已记录到 ShowFetchRun.error。
        - 没有想看电影时立即返回 0。
        """
        normalized_city_id = self._normalize_city_id(city_id)
        wished_movies = await asyncio.to_thread(movie_repository.list_wished_movies)
        movie_ids = [int(m.id) for m in wished_movies if m.id is not None]  # type: ignore[arg-type]

        run_id = await asyncio.to_thread(
            show_fetch_run_repository.create_started,
            _now_beijing_datetime(),
            len(movie_ids),
        )

        if not movie_ids:
            await asyncio.to_thread(
                show_fetch_run_repository.mark_finished,
                run_id,
                _now_beijing_datetime(),
                0,
                None,
            )
            logger.info("场次定时抓取:想看列表为空,跳过")
            return 0

        try:
            results = await show_fetcher.fetch_shows_for_selected_movies(
                movie_ids,
                city_id=normalized_city_id,
            )
            success_count = await self._persist_results(movie_ids, results)
            await asyncio.to_thread(
                show_fetch_run_repository.mark_finished,
                run_id,
                _now_beijing_datetime(),
                success_count,
                None,
            )
            logger.info(
                "场次定时抓取完成:%s/%s 部电影有场次",
                success_count,
                len(movie_ids),
            )
            return success_count
        except Exception as error:
            error_message = self._map_error(error)
            await asyncio.to_thread(
                show_fetch_run_repository.mark_finished,
                run_id,
                _now_beijing_datetime(),
                0,
                error_message,
            )
            logger.error("场次定时抓取失败: %s", error)
            return 0

    async def _persist_results(
        self,
        movie_ids: list[int],
        results: list[FinalMovieShowData],
    ) -> int:
        """把抓取结果按电影覆盖写入 movie_shows;无场次的电影也清空旧数据。"""
        results_by_movie: dict[int, FinalMovieShowData] = {result.movie_id: result for result in results}
        success_count = 0
        for movie_id in movie_ids:
            result = results_by_movie.get(movie_id)
            shows: list[MovieShowWriteData] = []
            if result is not None:
                for cinema in result.cinemas:
                    for show in cinema.shows:
                        shows.append({
                            "movie_id": movie_id,
                            "cinema_id": cinema.cinema_id,
                            "cinema_name": cinema.cinema_name,
                            "date": show.date,
                            "time": show.time,
                            "price": show.price,
                        })
            await asyncio.to_thread(movie_show_repository.replace_for_movie, movie_id, shows)
            if shows:
                success_count += 1
        return success_count

    async def get_shows_for_wished_movies(self) -> dict[str, object]:
        """返回前端需要的 wishMovies 场次结构 + 最近一次抓取完成时间。"""
        wished_movies = await asyncio.to_thread(movie_repository.list_wished_movies)
        movie_ids = [int(m.id) for m in wished_movies if m.id is not None]  # type: ignore[arg-type]
        shows = await asyncio.to_thread(movie_show_repository.list_for_movies, movie_ids)
        latest_run = await asyncio.to_thread(show_fetch_run_repository.get_latest_finished)

        movie_shows_map: dict[int, list[dict[str, object]]] = {mid: [] for mid in movie_ids}
        for show in shows:
            mid = int(show.movie_id)  # type: ignore[arg-type]
            if mid in movie_shows_map:
                movie_shows_map[mid].append({
                    "cinema_id": int(show.cinema_id),  # type: ignore[arg-type]
                    "cinema_name": str(show.cinema_name),
                    "date": str(show.date),
                    "time": str(show.time),
                    "price": None if show.price is None else str(show.price),
                })

        movies_payload = [
            {
                "movie_id": mid,
                "shows": movie_shows_map.get(mid, []),
            }
            for mid in movie_ids
        ]

        last_fetched_at = (
            latest_run.finished_at.isoformat() if latest_run and latest_run.finished_at else None  # type: ignore[union-attr]
        )

        return {
            "movies": movies_payload,
            "last_fetched_at": last_fetched_at,
        }

    def _normalize_city_id(self, city_id: int | None) -> int:
        normalized_city_id = city_id if city_id is not None else config_manager.city_id
        if normalized_city_id <= 0:
            raise AppError("city_id 必须是正整数", status_code=422)
        if normalized_city_id not in config_manager.city_mapping.values():
            raise AppError("city_id 不在当前支持的城市范围内", status_code=422)
        return normalized_city_id

    def _map_error(self, error: BaseException) -> str:
        if isinstance(error, RepositoryError):
            return "数据库访问失败"
        if isinstance(error, ExternalDependencyError):
            return "外部数据源请求失败"
        if isinstance(error, DataParsingError):
            return "外部数据解析失败"
        if isinstance(error, AppError):
            return error.message
        return f"未知错误: {error}"


show_service = ShowService()


__all__ = ["show_service", "ShowService"]
