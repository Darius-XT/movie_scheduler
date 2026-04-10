"""API 数据契约层。"""

from app.schemas.request_schema import SelectMovieRequest, UpdateCinemaRequest, UpdateMovieRequest
from app.schemas.response_schema import (
    CityItem,
    CityListResponse,
    MovieSelectionData,
    MovieSelectionItem,
    MovieSelectionResponse,
    UpdateCinemaData,
    UpdateCinemaResponse,
    UpdateMovieBaseInfo,
    UpdateMovieData,
    UpdateMovieDoubanInfo,
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
    "UpdateMovieDoubanInfo",
    "UpdateMovieExtraInfo",
    "UpdateMovieInputStats",
    "UpdateMovieResponse",
    "UpdateMovieRequest",
    "UpdateMovieResultStats",
]
