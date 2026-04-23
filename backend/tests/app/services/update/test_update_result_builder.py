"""更新结果组装器测试。"""

from dataclasses import asdict

from app.services.update.movie.base.entities import (
    MovieBaseInfoInputStats,
    MovieBaseInfoResultStats,
    MovieBaseInfoUpdateStats,
)
from app.services.update.result_builder import UpdateResultBuilder


def test_build_movie_update_result():
    """应按响应契约组装电影更新结果。"""
    builder = UpdateResultBuilder()

    result = builder.build_movie_update_result(
        base_info_stats=MovieBaseInfoUpdateStats(
            input_stats=MovieBaseInfoInputStats(
                scraped_total=10,
                showing=4,
                upcoming=5,
                duplicate=1,
                deduplicated_total=9,
            ),
            result_stats=MovieBaseInfoResultStats(
                existing=7,
                added=1,
                added_movie_ids=[101],
                updated=6,
                updated_movie_ids=[1, 2, 3, 4, 5, 6],
                removed=2,
                total=6,
            ),
        ),
        extra_info_updated_count=4,
    )

    assert asdict(result) == {
        "base_info": {
            "input_stats": {
                "scraped_total": 10,
                "showing": 4,
                "upcoming": 5,
                "duplicate": 1,
                "deduplicated_total": 9,
            },
            "result_stats": {
                "existing": 7,
                "added": 1,
                "added_movie_ids": [101],
                "updated": 6,
                "updated_movie_ids": [1, 2, 3, 4, 5, 6],
                "removed": 2,
                "total": 6,
            },
        },
        "extra_info": {"updated_count": 4},
    }


def test_build_cinema_update_result():
    """应按响应契约组装影院更新结果。"""
    builder = UpdateResultBuilder()

    result = builder.build_cinema_update_result(success_count=5, failure_count=1)

    assert asdict(result) == {"success_count": 5, "failure_count": 1}
