"""场次业务服务。"""

from __future__ import annotations

import asyncio
import queue
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass

from app.core.config import config_manager
from app.core.exceptions import AppError, DataParsingError, ExternalDependencyError, RepositoryError
from app.show.entities import ShowFetchProgressEvent
from app.show.fetcher import show_fetcher


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
        task = asyncio.create_task(self._fetch_to_queue(normalized_movie_ids, normalized_city_id, progress_queue))
        try:
            async for event in self._drain_queue(task, progress_queue):
                yield event
        except asyncio.CancelledError:
            task.cancel()
            raise

    async def _fetch_to_queue(
        self,
        movie_ids: list[int],
        city_id: int,
        progress_queue: queue.Queue[ShowStreamEvent],
    ) -> None:
        """在后台抓取场次并将事件写入队列。"""
        try:
            result = await show_fetcher.fetch_shows_for_selected_movies(
                movie_ids,
                city_id=city_id,
                progress_callback=lambda e: progress_queue.put(e),
            )
            progress_queue.put(StreamCompleteEvent(type="complete", data=[asdict(item) for item in result]))
        except Exception as error:
            progress_queue.put(StreamErrorEvent(type="error", error=self.map_stream_error(error)))

    async def _drain_queue(
        self,
        task: asyncio.Task[None],
        progress_queue: queue.Queue[ShowStreamEvent],
    ) -> AsyncIterator[ShowStreamEvent]:
        """从队列中持续取出事件直到完成或出错。"""
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
                    yield StreamErrorEvent(type="error", error=self.map_stream_error(error))
                return

    def _normalize_movie_ids(self, movie_ids: list[int]) -> list[int]:
        """校验并去重电影 ID 列表。"""
        if not movie_ids:
            raise AppError("movie_ids 不能为空", status_code=422)
        normalized: list[int] = []
        seen: set[int] = set()
        for movie_id in movie_ids:
            if movie_id <= 0:
                raise AppError("movie_ids 中包含无效电影 ID", status_code=422)
            if movie_id not in seen:
                seen.add(movie_id)
                normalized.append(movie_id)
        return normalized

    def _normalize_city_id(self, city_id: int | None) -> int:
        """校验并补全城市 ID。"""
        normalized_city_id = city_id if city_id is not None else config_manager.city_id
        if normalized_city_id <= 0:
            raise AppError("city_id 必须是正整数", status_code=422)
        if normalized_city_id not in config_manager.city_mapping.values():
            raise AppError("city_id 不在当前支持的城市范围内", status_code=422)
        return normalized_city_id

    def map_stream_error(self, error: Exception) -> str:
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
