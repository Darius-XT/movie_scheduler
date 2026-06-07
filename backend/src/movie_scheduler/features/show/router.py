"""场次接口。"""

from __future__ import annotations

from fastapi import APIRouter

from movie_scheduler.features.show.schemas import ShowsData, ShowsResponse
from movie_scheduler.features.show.service import show_service

router = APIRouter()


@router.get("/shows", response_model=ShowsResponse)
async def get_shows(movie_id: int | None = None) -> ShowsResponse:
    """返回想看电影的场次,可按 movie_id 限定单部电影。"""
    payload = await show_service.get_shows_for_wished_movies(movie_id=movie_id)
    return ShowsResponse(data=ShowsData(**payload))  # type: ignore[arg-type]
