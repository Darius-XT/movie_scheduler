"""场次业务服务。"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime
from typing import cast

from app.core.config import config_manager
from app.core.exceptions import AppError
from app.core.logger import logger
from app.models.movie_show import MovieShowWriteData
from app.repositories.movie import movie_repository
from app.repositories.movie_show import movie_show_repository
from app.show.fetcher import show_fetcher
from app.show.result_builder import FinalMovieShowData


class ShowService:
    """聚合场次抓取与持久化能力。"""

    async def refresh_wished_movie_shows(self, city_id: int | None = None) -> int:
        """抓取所有想看电影的场次并写入数据库,返回成功电影数。

        - 启动时与每小时触发一次,由调度器调用;不抛异常,失败只记录日志。
        - 没有想看电影时立即返回 0。
        """
        normalized_city_id = self._normalize_city_id(city_id)
        wished_movies = await asyncio.to_thread(movie_repository.list_wished_movies)
        movie_ids = [int(m.id) for m in wished_movies if m.id is not None]  # type: ignore[arg-type]

        if not movie_ids:
            logger.info("场次定时抓取:想看列表为空,跳过")
            return 0

        try:
            results = await show_fetcher.fetch_shows_for_selected_movies(
                movie_ids,
                city_id=normalized_city_id,
            )
            success_count = await self._persist_results(movie_ids, results)
            logger.info(
                "场次定时抓取完成:%s/%s 部电影有场次",
                success_count,
                len(movie_ids),
            )
            return success_count
        except Exception as error:
            logger.error("场次定时抓取失败: %s", error)
            return 0

    async def refresh_movie_shows(self, movie_id: int, city_id: int | None = None) -> int:
        """抓取单部想看电影的场次并写入数据库,返回写入场次的电影数。"""
        normalized_city_id = self._normalize_city_id(city_id)
        movie = await asyncio.to_thread(movie_repository.get_movie_by_id, movie_id)
        if movie is None:
            logger.warning("单片场次抓取跳过,电影不存在: %s", movie_id)
            return 0
        if not bool(movie.is_wished):
            await asyncio.to_thread(movie_show_repository.delete_for_movie, movie_id)
            logger.info("单片场次抓取跳过,电影不在想看: %s", movie_id)
            return 0

        try:
            results = await show_fetcher.fetch_shows_for_selected_movies(
                [movie_id],
                city_id=normalized_city_id,
            )
            success_count = await self._persist_results([movie_id], results)
            logger.info("单片场次抓取完成:电影 %s,成功数 %s", movie_id, success_count)
            return success_count
        except Exception as error:
            logger.error("单片场次抓取失败,电影 %s: %s", movie_id, error)
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
            if not await self._is_movie_wished(movie_id):
                await asyncio.to_thread(movie_show_repository.delete_for_movie, movie_id)
                continue
            result = results_by_movie.get(movie_id)
            shows: list[MovieShowWriteData] = []
            if result is not None:
                for cinema in result.cinemas:
                    for show in cinema.shows:
                        shows.append(
                            {
                                "movie_id": movie_id,
                                "cinema_id": cinema.cinema_id,
                                "cinema_name": cinema.cinema_name,
                                "date": show.date,
                                "time": show.time,
                                "price": show.price,
                            }
                        )
            await asyncio.to_thread(movie_show_repository.replace_for_movie, movie_id, shows)
            await asyncio.to_thread(movie_repository.touch_shows_updated_at, movie_id)
            if shows:
                success_count += 1
        return success_count

    async def get_shows_for_wished_movies(self, movie_id: int | None = None) -> dict[str, object]:
        """返回前端需要的 wishMovies 场次结构 + 最近一次抓取完成时间。"""
        if movie_id is not None:
            return await self._get_shows_for_single_wished_movie(movie_id)

        wished_movies = await asyncio.to_thread(movie_repository.list_wished_movies)
        movie_ids = [int(m.id) for m in wished_movies if m.id is not None]  # type: ignore[arg-type]
        shows = await asyncio.to_thread(movie_show_repository.list_for_movies, movie_ids)
        latest = await asyncio.to_thread(movie_repository.get_latest_shows_updated_at, movie_ids)

        return {
            "movies": self._build_movies_payload(movie_ids, shows),
            "last_fetched_at": self._serialize_datetime(latest),
        }

    async def _get_shows_for_single_wished_movie(self, movie_id: int) -> dict[str, object]:
        """返回单部想看电影的场次结构。"""
        movie = await asyncio.to_thread(movie_repository.get_movie_by_id, movie_id)
        if movie is None:
            raise AppError(f"电影不存在: {movie_id}", status_code=404)
        if not bool(movie.is_wished):
            return {
                "movies": [],
                "last_fetched_at": None,
            }

        shows = await asyncio.to_thread(movie_show_repository.list_for_movies, [movie_id])
        shows_updated_at = cast(datetime | None, getattr(movie, "shows_updated_at", None))
        return {
            "movies": self._build_movies_payload([movie_id], shows),
            "last_fetched_at": self._serialize_datetime(shows_updated_at),
        }

    def _normalize_city_id(self, city_id: int | None) -> int:
        normalized_city_id = city_id if city_id is not None else config_manager.city_id
        if normalized_city_id <= 0:
            raise AppError("city_id 必须是正整数", status_code=422)
        if normalized_city_id not in config_manager.city_mapping.values():
            raise AppError("city_id 不在当前支持的城市范围内", status_code=422)
        return normalized_city_id

    async def _is_movie_wished(self, movie_id: int) -> bool:
        movie = await asyncio.to_thread(movie_repository.get_movie_by_id, movie_id)
        return bool(movie and movie.is_wished)

    def _build_movies_payload(self, movie_ids: list[int], shows: Sequence[object]) -> list[dict[str, object]]:
        movie_shows_map: dict[int, list[dict[str, object]]] = {mid: [] for mid in movie_ids}
        for show in shows:
            mid = int(getattr(show, "movie_id"))
            if mid in movie_shows_map:
                movie_shows_map[mid].append(
                    {
                        "cinema_id": int(getattr(show, "cinema_id")),
                        "cinema_name": str(getattr(show, "cinema_name")),
                        "date": str(getattr(show, "date")),
                        "time": str(getattr(show, "time")),
                        "price": self._serialize_optional(getattr(show, "price")),
                    }
                )
        return [
            {
                "movie_id": mid,
                "shows": movie_shows_map.get(mid, []),
            }
            for mid in movie_ids
        ]

    def _serialize_optional(self, value: object) -> str | None:
        return None if value is None else str(value)

    def _serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


show_service = ShowService()


__all__ = ["show_service", "ShowService"]
