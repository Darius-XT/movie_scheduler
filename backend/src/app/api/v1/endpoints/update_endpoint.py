"""信息更新接口。"""

from fastapi import APIRouter

from app.schemas import (
    UpdateCinemaData,
    UpdateCinemaRequest,
    UpdateCinemaResponse,
    UpdateMovieBaseInfo,
    UpdateMovieData,
    UpdateMovieExtraInfo,
    UpdateMovieInputStats,
    UpdateMovieRequest,
    UpdateMovieResponse,
    UpdateMovieResultStats,
)
from app.services.update_service import update_service

router = APIRouter()


@router.post("/update/cinema", response_model=UpdateCinemaResponse)
async def update_cinema(request: UpdateCinemaRequest) -> UpdateCinemaResponse:
    """更新影院信息。"""
    result = await update_service.update_cinema(city_id=request.city_id)
    return UpdateCinemaResponse(
        data=UpdateCinemaData(
            success_count=result.success_count,
            failure_count=result.failure_count,
        )
    )


@router.post("/update/movie", response_model=UpdateMovieResponse)
async def update_movie(request: UpdateMovieRequest) -> UpdateMovieResponse:
    """更新电影信息。"""
    result = await update_service.update_movie(
        city_id=request.city_id,
        force_update_all=request.force_update_all,
    )
    return UpdateMovieResponse(
        data=UpdateMovieData(
            base_info=UpdateMovieBaseInfo(
                input_stats=UpdateMovieInputStats(
                    scraped_total=result.base_info.input_stats.scraped_total,
                    showing=result.base_info.input_stats.showing,
                    upcoming=result.base_info.input_stats.upcoming,
                    duplicate=result.base_info.input_stats.duplicate,
                    deduplicated_total=result.base_info.input_stats.deduplicated_total,
                ),
                result_stats=UpdateMovieResultStats(
                    existing=result.base_info.result_stats.existing,
                    added=result.base_info.result_stats.added,
                    added_movie_ids=result.base_info.result_stats.added_movie_ids,
                    updated=result.base_info.result_stats.updated,
                    updated_movie_ids=result.base_info.result_stats.updated_movie_ids,
                    removed=result.base_info.result_stats.removed,
                    total=result.base_info.result_stats.total,
                ),
            ),
            extra_info=UpdateMovieExtraInfo(updated_count=result.extra_info.updated_count),
        )
    )
