"""信息更新接口。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Callable

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.exceptions import AppError, RepositoryError
from app.update.entities import UpdateProgressEvent
from app.update.result_builder import UpdateCinemaResult, UpdateMovieResult
from app.update.schemas import (
    FetchMovieDoubanData,
    FetchMovieDoubanResponse,
    UpdateCinemaData,
    UpdateMovieBaseInfo,
    UpdateMovieData,
    UpdateMovieExtraInfo,
    UpdateMovieInputStats,
    UpdateMovieResultStats,
)
from app.update.service import update_service

router = APIRouter()


def build_update_movie_data(result: UpdateMovieResult) -> UpdateMovieData:
    """将电影更新结果转换为响应数据对象。"""
    return UpdateMovieData(
        base_info=UpdateMovieBaseInfo(
            input_stats=UpdateMovieInputStats(
                scraped_total=result.base_info.input_stats.scraped_total,
                showing=result.base_info.input_stats.showing,
                upcoming=result.base_info.input_stats.upcoming,
                duplicate=result.base_info.input_stats.duplicate,
                deduplicated_total=result.base_info.input_stats.deduplicated_total,
            ),
            result_stats=UpdateMovieResultStats(
                existing=result.base_info.result_stats.existing,
                added=result.base_info.result_stats.added,
                added_movie_ids=result.base_info.result_stats.added_movie_ids,
                updated=result.base_info.result_stats.updated,
                updated_movie_ids=result.base_info.result_stats.updated_movie_ids,
                removed=result.base_info.result_stats.removed,
                total=result.base_info.result_stats.total,
            ),
        ),
        extra_info=UpdateMovieExtraInfo(updated_count=result.extra_info.updated_count),
    )


def build_update_cinema_data(result: UpdateCinemaResult) -> UpdateCinemaData:
    """将影院更新结果转换为响应数据对象。"""
    return UpdateCinemaData(success_count=result.success_count, failure_count=result.failure_count)


def map_update_stream_error(error: Exception) -> str:
    """将更新流中的异常映射为稳定的前端可读消息。"""
    if isinstance(error, AppError):
        return error.message
    if isinstance(error, RepositoryError):
        return "数据库访问失败，请稍后重试"
    return "更新失败，请稍后重试"


def _make_progress_pusher(
    loop: asyncio.AbstractEventLoop,
    event_queue: asyncio.Queue[dict[str, object] | None],
) -> Callable[[UpdateProgressEvent], None]:
    """构建将进度事件写入队列的回调（线程安全，可从工作线程调用）。"""
    def push_progress(event: UpdateProgressEvent) -> None:
        payload: dict[str, object] = {
            "type": "progress", "stage": event.stage, "message": event.message,
            "current": event.current, "total": event.total,
            "city_id": event.city_id, "page": event.page,
        }
        loop.call_soon_threadsafe(event_queue.put_nowait, payload)
    return push_progress


async def _drain_sse_queue(
    event_queue: asyncio.Queue[dict[str, object] | None],
    task: asyncio.Task[None],
) -> AsyncIterator[str]:
    """从队列中取出事件并编码为 SSE 帧，直到任务完成。"""
    try:
        while True:
            event = await event_queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False, separators=(',', ':'))}\n\n"
    finally:
        if not task.done():
            task.cancel()


async def encode_update_movie_stream(city_id: int, force_update_all: bool) -> AsyncIterator[str]:
    """将电影更新过程编码为 SSE 文本帧。"""
    event_queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    push_progress = _make_progress_pusher(loop, event_queue)

    async def run_update() -> None:
        try:
            result = await update_service.update_movie(
                city_id=city_id, force_update_all=force_update_all,
                progress_callback=push_progress,
            )
            payload: dict[str, object] = {"type": "complete", "data": build_update_movie_data(result).model_dump()}
            loop.call_soon_threadsafe(event_queue.put_nowait, payload)
        except Exception as error:
            error_payload: dict[str, object] = {"type": "error", "error": map_update_stream_error(error)}
            loop.call_soon_threadsafe(event_queue.put_nowait, error_payload)
        finally:
            loop.call_soon_threadsafe(event_queue.put_nowait, None)

    task = asyncio.create_task(run_update())
    async for frame in _drain_sse_queue(event_queue, task):
        yield frame


async def encode_update_cinema_stream(city_id: int, force_update_all: bool) -> AsyncIterator[str]:
    """将影院更新过程编码为 SSE 文本帧。"""
    event_queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    push_progress = _make_progress_pusher(loop, event_queue)

    async def run_update() -> None:
        try:
            result = await update_service.update_cinema(
                city_id=city_id, force_update_all=force_update_all,
                progress_callback=push_progress,
            )
            payload: dict[str, object] = {"type": "complete", "data": build_update_cinema_data(result).model_dump()}
            loop.call_soon_threadsafe(event_queue.put_nowait, payload)
        except Exception as error:
            error_payload: dict[str, object] = {"type": "error", "error": map_update_stream_error(error)}
            loop.call_soon_threadsafe(event_queue.put_nowait, error_payload)
        finally:
            loop.call_soon_threadsafe(event_queue.put_nowait, None)

    task = asyncio.create_task(run_update())
    async for frame in _drain_sse_queue(event_queue, task):
        yield frame


@router.get("/update/movie-stream")
async def update_movie_stream(city_id: int, force_update_all: bool = False) -> StreamingResponse:
    """以 SSE 方式流式返回电影更新文案进度。"""
    return StreamingResponse(
        encode_update_movie_stream(city_id=city_id, force_update_all=force_update_all),
        media_type="text/event-stream",
    )


@router.get("/update/cinema-stream")
async def update_cinema_stream(city_id: int, force_update_all: bool = False) -> StreamingResponse:
    """以 SSE 方式流式返回影院更新文案进度。"""
    return StreamingResponse(
        encode_update_cinema_stream(city_id=city_id, force_update_all=force_update_all),
        media_type="text/event-stream",
    )


@router.post("/movies/{movie_id}/fetch-douban", response_model=FetchMovieDoubanResponse)
async def fetch_movie_douban(movie_id: int) -> FetchMovieDoubanResponse:
    """为单部电影抓取豆瓣评分与详情链接。"""
    supplement = await update_service.fetch_douban_for_movie(movie_id)
    return FetchMovieDoubanResponse(
        data=FetchMovieDoubanData(score=supplement.score, douban_url=supplement.douban_url),
    )
