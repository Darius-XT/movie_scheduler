"""场次接口。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from movie_scheduler.features.show.schemas import ShowsData, ShowsResponse
from movie_scheduler.features.show.service import show_service

router = APIRouter()


@router.get("/shows", response_model=ShowsResponse)
async def get_shows(movie_id: int | None = None) -> ShowsResponse:
    """返回想看电影的场次,可按 movie_id 限定单部电影。"""
    payload = await show_service.get_shows_for_wished_movies(movie_id=movie_id)
    return ShowsResponse(data=ShowsData(**payload))  # type: ignore[arg-type]


@router.get("/shows/update-stream")
async def update_shows_stream(city_id: int) -> StreamingResponse:
    """以 SSE 方式流式返回想看电影的场次更新进度。"""
    return StreamingResponse(
        show_service.stream_show_update(city_id=city_id),
        media_type="text/event-stream",
    )
