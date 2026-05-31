"""场次接口。"""

from __future__ import annotations

from fastapi import APIRouter

from app.show.schemas import ShowsData, ShowsResponse
from app.show.service import show_service

router = APIRouter()


@router.get("/shows", response_model=ShowsResponse)
async def get_shows() -> ShowsResponse:
    """返回想看电影的全部场次,以及最近一次抓取完成时间。"""
    payload = await show_service.get_shows_for_wished_movies()
    return ShowsResponse(data=ShowsData(**payload))  # type: ignore[arg-type]
