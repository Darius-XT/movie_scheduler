"""电影接口。"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from app.movie.schemas import (
    MovieDetailData,
    MovieDetailResponse,
    MovieSelectionData,
    MovieSelectionItem,
    MovieSelectionResponse,
    SelectMovieRequest,
    SetMovieWishedRequest,
    WishedMoviesData,
    WishedMoviesResponse,
)
from app.movie.service import movie_service

router = APIRouter()


@router.post("/movies/select", response_model=MovieSelectionResponse)
async def select_movie(request: SelectMovieRequest) -> MovieSelectionResponse:
    """按上映状态筛选电影。"""
    movies = await movie_service.select_movie(selection_mode=request.selection_mode)
    movie_items = [MovieSelectionItem(**asdict(movie)) for movie in movies]
    return MovieSelectionResponse(data=MovieSelectionData(movies=movie_items))


@router.get("/movies/wished", response_model=WishedMoviesResponse)
async def list_wished_movies() -> WishedMoviesResponse:
    """读取全部想看电影。"""
    movies = await movie_service.list_wished_movies()
    movie_items = [MovieSelectionItem(**asdict(movie)) for movie in movies]
    return WishedMoviesResponse(data=WishedMoviesData(movies=movie_items))


@router.patch("/movies/{movie_id}/wished", response_model=MovieDetailResponse)
async def set_movie_wished(movie_id: int, request: SetMovieWishedRequest) -> MovieDetailResponse:
    """更新单部电影的想看状态。"""
    movie = await movie_service.set_movie_wished(movie_id, request.is_wished)
    return MovieDetailResponse(data=MovieDetailData(movie=MovieSelectionItem(**asdict(movie))))
