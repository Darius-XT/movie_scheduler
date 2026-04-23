"""API 数据契约层。"""

from app.schemas.request import SelectMovieRequest, UpdateCinemaRequest, UpdateMovieRequest
from app.schemas.response import (
    CityItem,
    CityListResponse,
    MovieSelectionData,
    MovieSelectionItem,
    MovieSelectionResponse,
    UpdateCinemaData,
    UpdateCinemaResponse,
    UpdateMovieBaseInfo,
    UpdateMovieData,
    UpdateMovieExtraInfo,
    UpdateMovieInputStats,
    UpdateMovieResponse,
    UpdateMovieResultStats,
)

__all__ = [
    "CityItem",
    "CityListResponse",
    "MovieSelectionData",
    "MovieSelectionItem",
    "MovieSelectionResponse",
    "SelectMovieRequest",
    "UpdateCinemaData",
    "UpdateCinemaResponse",
    "UpdateCinemaRequest",
    "UpdateMovieBaseInfo",
    "UpdateMovieData",
    "UpdateMovieExtraInfo",
    "UpdateMovieInputStats",
    "UpdateMovieResponse",
    "UpdateMovieRequest",
    "UpdateMovieResultStats",
]
