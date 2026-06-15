"""电影接口。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from movie_scheduler.features.movie.schemas import (
    MovieDetailData,
    MovieDetailResponse,
    MovieSelectionData,
    MovieSelectionItem,
    MovieSelectionResponse,
    MovieUpdateStatusData,
    MovieUpdateStatusResponse,
    SelectMovieRequest,
    SetMovieWishedRequest,
    UpdateMovieDoubanData,
    UpdateMovieDoubanResponse,
    WishedMoviesData,
    WishedMoviesResponse,
)
from movie_scheduler.features.movie.service import movie_service

router = APIRouter()


@router.post("/movies/select", response_model=MovieSelectionResponse)
async def select_movie(request: SelectMovieRequest) -> MovieSelectionResponse:
    """按上映状态筛选电影。"""
    movies = await movie_service.select_movie(selection_mode=request.selection_mode)
    movie_items = [MovieSelectionItem(**movie) for movie in movies]  # type: ignore[arg-type]
    return MovieSelectionResponse(data=MovieSelectionData(movies=movie_items))


@router.get("/movies/wished", response_model=WishedMoviesResponse)
async def list_wished_movies() -> WishedMoviesResponse:
    """读取全部想看电影。"""
    movies = await movie_service.list_wished_movies()
    movie_items = [MovieSelectionItem(**movie) for movie in movies]  # type: ignore[arg-type]
    return WishedMoviesResponse(data=WishedMoviesData(movies=movie_items))


@router.patch("/movies/{movie_id}/wished", response_model=MovieDetailResponse)
async def set_movie_wished(movie_id: int, request: SetMovieWishedRequest) -> MovieDetailResponse:
    """更新单部电影的想看状态。"""
    movie = await movie_service.set_movie_wished(movie_id, request.is_wished)
    return MovieDetailResponse(data=MovieDetailData(movie=MovieSelectionItem(**movie)))  # type: ignore[arg-type]


@router.get("/movies/update-status", response_model=MovieUpdateStatusResponse)
async def get_movie_update_status() -> MovieUpdateStatusResponse:
    """返回电影定时更新的最后一次完成时间。"""
    last_updated_at = await movie_service.get_movies_last_updated_at()
    return MovieUpdateStatusResponse(
        data=MovieUpdateStatusData(
            last_updated_at=last_updated_at.isoformat() if last_updated_at else None,
        ),
    )


@router.get("/movies/update-stream")
async def update_movies_stream(city_id: int) -> StreamingResponse:
    """以 SSE 方式流式返回电影更新进度(增量)。"""
    return StreamingResponse(
        movie_service.stream_movie_update(city_id=city_id),
        media_type="text/event-stream",
    )


@router.post("/movies/{movie_id}/update-douban", response_model=UpdateMovieDoubanResponse)
async def update_movie_douban(movie_id: int) -> UpdateMovieDoubanResponse:
    """为单部电影抓取豆瓣评分与详情链接。"""
    supplement = await movie_service.update_movie_douban(movie_id)
    return UpdateMovieDoubanResponse(
        data=UpdateMovieDoubanData(score=supplement.score, douban_url=supplement.douban_url),
    )
