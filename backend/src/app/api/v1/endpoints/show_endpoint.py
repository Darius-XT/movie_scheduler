"""场次接口。"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import asdict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.show_service import ShowStreamEvent, StreamErrorEvent, show_service

router = APIRouter()


async def encode_show_stream(events: AsyncIterator[ShowStreamEvent]) -> AsyncIterator[str]:
    """将结构化事件编码为 SSE 文本帧。"""
    try:
        async for event in events:
            yield f"data: {json.dumps(asdict(event), ensure_ascii=False, separators=(',', ':'))}\n\n"
    except Exception as error:
        masked_error = StreamErrorEvent(
            type="error",
            error=show_service._map_stream_error(error),  # pyright: ignore[reportPrivateUsage]
        )
        yield f"data: {json.dumps(asdict(masked_error), ensure_ascii=False, separators=(',', ':'))}\n\n"


@router.get("/shows/fetch-stream")
async def fetch_show_stream(movie_ids: str, city_id: int | None = None) -> StreamingResponse:
    """以 SSE 方式流式返回电影场次。"""
    movie_id_list = [int(movie_id.strip()) for movie_id in movie_ids.split(",") if movie_id.strip()]
    return StreamingResponse(
        encode_show_stream(show_service.stream_show(movie_ids=movie_id_list, city_id=city_id)),
        media_type="text/event-stream",
    )
