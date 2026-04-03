"""电影接口。"""

from dataclasses import asdict

from fastapi import APIRouter

from app.schemas import (
    MovieSelectionData,
    MovieSelectionItem,
    MovieSelectionResponse,
    SelectMovieRequest,
)
from app.services.movie_service import movie_service

router = APIRouter()


@router.post("/movies/select", response_model=MovieSelectionResponse)
async def select_movie(request: SelectMovieRequest) -> MovieSelectionResponse:
    """按上映状态筛选电影。"""
    movies = await movie_service.select_movie(selection_mode=request.selection_mode)
    movie_items = [MovieSelectionItem(**asdict(movie)) for movie in movies]
    return MovieSelectionResponse(data=MovieSelectionData(movies=movie_items))
