"""影院接口。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from movie_scheduler.features.cinema.service import cinema_service

router = APIRouter()


@router.get("/cinemas/update-stream")
async def update_cinemas_stream(city_id: int) -> StreamingResponse:
    """以 SSE 方式流式返回影院更新文案进度(增量)。"""
    return StreamingResponse(
        cinema_service.stream_cinema_update(city_id=city_id),
        media_type="text/event-stream",
    )
