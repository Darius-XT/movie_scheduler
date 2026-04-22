"""电影接口。"""

from __future__ import annotations

from dataclasses import asdict
from typing import cast

from fastapi import APIRouter, HTTPException

from app.models.movie import MovieWriteData
from app.repositories.movie_repository import movie_repository
from app.schemas import (
    MovieSelectionData,
    MovieSelectionItem,
    MovieSelectionResponse,
    SelectMovieRequest,
)
from app.services.movie_service import movie_service
from app.use_cases.update.movie_info.douban.douban_info_enricher import (
    SupportsDoubanMatchingMovie,
    douban_info_enricher,
)

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
    movie = movie_repository.get_movie_by_id(movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="电影不存在")

    supplement = douban_info_enricher.fetch_movie_supplement(cast(SupportsDoubanMatchingMovie, movie))
    movie_repository.save_movie(
        cast(MovieWriteData, {"id": movie_id, "title": getattr(movie, "title", None), "score": supplement.score, "douban_url": supplement.douban_url})
    )
    return {"score": supplement.score, "douban_url": supplement.douban_url}
