"""场次业务服务。"""

from __future__ import annotations

import asyncio
import queue
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass

from app.core.config import config_manager
from app.core.exceptions import AppError, DataParsingError, ExternalDependencyError, RepositoryError
from app.use_cases.show_fetching.fetcher import show_fetcher
from app.use_cases.show_fetching.models import ShowFetchProgressEvent


@dataclass(slots=True)
class StreamCompleteEvent:
    """流式抓取完成事件。"""

    type: str
    data: list[dict[str, object]]


@dataclass(slots=True)
class StreamErrorEvent:
    """流式抓取失败事件。"""

    type: str
    error: str


ShowStreamEvent = ShowFetchProgressEvent | StreamCompleteEvent | StreamErrorEvent


class ShowService:
    """聚合场次抓取与流式推送能力。"""

    async def stream_show(
        self,
        movie_ids: list[int],
        city_id: int | None = None,
    ) -> AsyncIterator[ShowStreamEvent]:
        """流式抓取电影场次，并返回结构化事件。"""
        normalized_movie_ids = self._normalize_movie_ids(movie_ids)
        normalized_city_id = self._normalize_city_id(city_id)
        progress_queue: queue.Queue[ShowStreamEvent] = queue.Queue()

        def progress_callback(progress_data: ShowFetchProgressEvent) -> None:
            """收集抓取进度。"""
            progress_queue.put(progress_data)

        async def fetch_task() -> None:
            try:
                result = await show_fetcher.fetch_shows_for_selected_movies(
                    normalized_movie_ids,
                    city_id=normalized_city_id,
                    progress_callback=progress_callback,
                )
                progress_queue.put(
                    StreamCompleteEvent(
                        type="complete",
                        data=[asdict(item) for item in result],
                    )
                )
            except Exception as error:
                progress_queue.put(StreamErrorEvent(type="error", error=self._map_stream_error(error)))

        task = asyncio.create_task(fetch_task())

        try:
            while True:
                await asyncio.sleep(0.1)
                updates: list[ShowStreamEvent] = []
                try:
                    while not progress_queue.empty():
                        updates.append(progress_queue.get_nowait())
                except queue.Empty:
                    pass

                for update in updates:
                    yield update
                    if update.type in ["complete", "error"]:
                        return

                if task.done():
                    try:
                        task.result()
                    except Exception as error:
                        yield StreamErrorEvent(type="error", error=self._map_stream_error(error))
                    return
        except asyncio.CancelledError:
            task.cancel()
            raise

    def _normalize_movie_ids(self, movie_ids: list[int]) -> list[int]:
        """校验并去重电影 ID 列表。"""
        if not movie_ids:
            raise AppError("movie_ids 不能为空", status_code=422)

        normalized_movie_ids: list[int] = []
        seen_ids: set[int] = set()
        for movie_id in movie_ids:
            if movie_id <= 0:
                raise AppError("movie_ids 中包含无效电影 ID", status_code=422)
            if movie_id in seen_ids:
                continue
            seen_ids.add(movie_id)
            normalized_movie_ids.append(movie_id)

        return normalized_movie_ids

    def _normalize_city_id(self, city_id: int | None) -> int:
        """校验并补全城市 ID。"""
        normalized_city_id = city_id if city_id is not None else config_manager.city_id
        if normalized_city_id <= 0:
            raise AppError("city_id 必须是正整数", status_code=422)
        if normalized_city_id not in config_manager.city_mapping.values():
            raise AppError("city_id 不在当前支持的城市范围内", status_code=422)
        return normalized_city_id

    def _map_stream_error(self, error: Exception) -> str:
        """将内部异常映射为稳定的流式错误消息。"""
        if isinstance(error, RepositoryError):
            return "数据库访问失败，请稍后重试"
        if isinstance(error, ExternalDependencyError):
            return "外部数据源请求失败，请稍后重试"
        if isinstance(error, DataParsingError):
            return "外部数据解析失败，请稍后重试"
        if isinstance(error, AppError):
            return error.message
        return "服务器内部错误"


show_service = ShowService()
