"""电影接口。"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from app.schemas import (
    MovieSelectionData,
    MovieSelectionItem,
    MovieSelectionResponse,
    SelectMovieRequest,
)
from app.services.movie_selection.service import movie_service
from app.services.update.service import update_service

router = APIRouter()


@router.post("/movies/select", response_model=MovieSelectionResponse)
async def select_movie(request: SelectMovieRequest) -> MovieSelectionResponse:
    """按上映状态筛选电影。"""
    movies = await movie_service.select_movie(selection_mode=request.selection_mode)
    movie_items = [MovieSelectionItem(**asdict(movie)) for movie in movies]
    return MovieSelectionResponse(data=MovieSelectionData(movies=movie_items))


@router.post("/movies/{movie_id}/fetch-douban")
async def fetch_movie_douban(movie_id: int) -> dict[str, str | None]:
    """为单部电影抓取豆瓣评分与详情链接。"""
    supplement = await update_service.fetch_douban_for_movie(movie_id)
    return {"score": supplement.score, "douban_url": supplement.douban_url}
