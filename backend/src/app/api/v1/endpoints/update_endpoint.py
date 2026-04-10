"""信息更新接口。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.exceptions import AppError, RepositoryError
from app.schemas import (
    UpdateCinemaData,
    UpdateMovieBaseInfo,
    UpdateMovieData,
    UpdateMovieDoubanInfo,
    UpdateMovieExtraInfo,
    UpdateMovieInputStats,
    UpdateMovieResultStats,
)
from app.services.update_service import update_service
from app.use_cases.update.models import UpdateProgressEvent
from app.use_cases.update.update_result_builder import UpdateCinemaResult, UpdateMovieResult

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
        douban_info=UpdateMovieDoubanInfo(updated_count=result.douban_info.updated_count),
    )


def build_update_cinema_data(result: UpdateCinemaResult) -> UpdateCinemaData:
    """将影院更新结果转换为响应数据对象。"""
    return UpdateCinemaData(
        success_count=result.success_count,
        failure_count=result.failure_count,
    )


def map_update_stream_error(error: Exception) -> str:
    """将更新流中的异常映射为稳定的前端可读消息。"""
    if isinstance(error, AppError):
        return error.message
    if isinstance(error, RepositoryError):
        return "数据库访问失败，请稍后重试"
    return "更新失败，请稍后重试"


async def encode_update_movie_stream(
    city_id: int,
    force_update_all: bool,
) -> AsyncIterator[str]:
    """将电影更新过程编码为 SSE 文本帧。"""
    event_queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

    def push_progress(event: UpdateProgressEvent) -> None:
        event_queue.put_nowait(
            {
                "type": "progress",
                "stage": event.stage,
                "message": event.message,
                "current": event.current,
                "total": event.total,
                "city_id": event.city_id,
                "page": event.page,
            }
        )

    async def run_update() -> None:
        try:
            result = await update_service.update_movie(
                city_id=city_id,
                force_update_all=force_update_all,
                progress_callback=push_progress,
            )
            await event_queue.put(
                {
                    "type": "complete",
                    "data": build_update_movie_data(result).model_dump(),
                }
            )
        except Exception as error:
            await event_queue.put(
                {
                    "type": "error",
                    "error": map_update_stream_error(error),
                }
            )
        finally:
            await event_queue.put(None)

    update_task = asyncio.create_task(run_update())

    try:
        while True:
            event = await event_queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False, separators=(',', ':'))}\n\n"
    finally:
        if not update_task.done():
            update_task.cancel()


async def encode_update_cinema_stream(city_id: int) -> AsyncIterator[str]:
    """将影院更新过程编码为 SSE 文本帧。"""
    event_queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()

    def push_progress(event: UpdateProgressEvent) -> None:
        event_queue.put_nowait(
            {
                "type": "progress",
                "stage": event.stage,
                "message": event.message,
                "current": event.current,
                "total": event.total,
                "city_id": event.city_id,
                "page": event.page,
            }
        )

    async def run_update() -> None:
        try:
            result = await update_service.update_cinema(
                city_id=city_id,
                progress_callback=push_progress,
            )
            await event_queue.put(
                {
                    "type": "complete",
                    "data": build_update_cinema_data(result).model_dump(),
                }
            )
        except Exception as error:
            await event_queue.put(
                {
                    "type": "error",
                    "error": map_update_stream_error(error),
                }
            )
        finally:
            await event_queue.put(None)

    update_task = asyncio.create_task(run_update())

    try:
        while True:
            event = await event_queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False, separators=(',', ':'))}\n\n"
    finally:
        if not update_task.done():
            update_task.cancel()


@router.get("/update/movie-stream")
async def update_movie_stream(
    city_id: int,
    force_update_all: bool = False,
) -> StreamingResponse:
    """以 SSE 方式流式返回电影更新文案进度。"""
    return StreamingResponse(
        encode_update_movie_stream(city_id=city_id, force_update_all=force_update_all),
        media_type="text/event-stream",
    )


@router.get("/update/cinema-stream")
async def update_cinema_stream(city_id: int) -> StreamingResponse:
    """以 SSE 方式流式返回影院更新文案进度。"""
    return StreamingResponse(
        encode_update_cinema_stream(city_id=city_id),
        media_type="text/event-stream",
    )
