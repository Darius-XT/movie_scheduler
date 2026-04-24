"""场次抓取流程测试。"""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import cast

import pytest

from app.core.exceptions import ExternalDependencyError, RepositoryError
from app.show.fetcher import ShowForSelectedMovieFetcher
from app.show.entities import FetchedShowItem, ShowFetchProgressEvent
from app.show.result_builder import MovieShowDataBuilder
from app.show.gateway import ShowGateway


class FakeShowGateway:
    """用于测试的场次抓取网关。"""

    def get_movie_name(self, movie_id: int) -> str:
        return f"电影{movie_id}"

    def get_show_dates(self, movie_id: int, city_id: int) -> list[str]:
        assert movie_id == 1
        assert city_id == 10
        return ["2026-04-05", "2026-04-06"]

    def get_cinemas(self, movie_id: int, show_date: str, city_id: int) -> list[int]:
        assert movie_id == 1
        assert show_date in {"2026-04-05", "2026-04-06"}
        assert city_id == 10
        return [10, 20]

    def get_cinema_shows(
        self,
        cinema_id: int,
        movie_name: str,
        city_id: int,
        show_date: str | None = None,
    ) -> list[FetchedShowItem]:
        assert movie_name == "电影1"
        assert city_id == 10
        assert show_date in {"2026-04-05", "2026-04-06"}
        return [
            FetchedShowItem(
                movie_id=1,
                movie_name=movie_name,
                cinema_id=cinema_id,
                cinema_name=f"影院{cinema_id}",
                show_date=show_date or "2026-04-05",
                show_time="18:00" if cinema_id == 10 else "20:00",
                price="30" if cinema_id == 10 else "35",
            )
        ]


def test_fetcher_builds_complete_movie_result() -> None:
    """场次抓取流程应正确聚合电影、影院和场次数据。"""
    progress_events: list[ShowFetchProgressEvent] = []
    fetcher = ShowForSelectedMovieFetcher(
        gateway=cast(ShowGateway, FakeShowGateway()),
        builder=MovieShowDataBuilder(),
    )

    result = asyncio.run(
        fetcher.fetch_shows_for_selected_movies(
            [1],
            city_id=10,
            progress_callback=progress_events.append,
        )
    )

    assert [asdict(item) for item in result] == [
        {
            "movie_id": 1,
            "cinemas": [
                {
                    "cinema_id": 10,
                    "cinema_name": "影院10",
                    "shows": [
                        {"date": "2026-04-05", "time": "18:00", "price": "30"},
                        {"date": "2026-04-06", "time": "18:00", "price": "30"},
                    ],
                },
                {
                    "cinema_id": 20,
                    "cinema_name": "影院20",
                    "shows": [
                        {"date": "2026-04-05", "time": "20:00", "price": "35"},
                        {"date": "2026-04-06", "time": "20:00", "price": "35"},
                    ],
                },
            ],
        }
    ]
    event_types = [event.type for event in progress_events]
    assert event_types[0] == "dates_found"
    assert event_types[-1] == "movie_complete"
    assert event_types.count("processing_date") == 2
    assert event_types.count("processing_cinema") == 4


def test_fetcher_skips_movie_when_degradable_error_occurs() -> None:
    """可降级错误应只跳过当前电影，不中断整次抓取。"""

    class PartiallyFailingGateway(FakeShowGateway):
        def get_show_dates(self, movie_id: int, city_id: int) -> list[str]:
            if movie_id == 2:
                raise ExternalDependencyError("排片接口超时")
            return super().get_show_dates(movie_id, city_id)

    fetcher = ShowForSelectedMovieFetcher(
        gateway=cast(ShowGateway, PartiallyFailingGateway()),
        builder=MovieShowDataBuilder(),
    )

    result = asyncio.run(fetcher.fetch_shows_for_selected_movies([1, 2], city_id=10))

    assert [item.movie_id for item in result] == [1]


def test_fetcher_raises_when_critical_error_occurs() -> None:
    """不可恢复错误应中断整次抓取。"""

    class CriticallyFailingGateway(FakeShowGateway):
        def get_movie_name(self, movie_id: int) -> str:
            if movie_id == 2:
                raise RepositoryError("数据库读取失败")
            return super().get_movie_name(movie_id)

    fetcher = ShowForSelectedMovieFetcher(
        gateway=cast(ShowGateway, CriticallyFailingGateway()),
        builder=MovieShowDataBuilder(),
    )

    with pytest.raises(RepositoryError):
        asyncio.run(fetcher.fetch_shows_for_selected_movies([1, 2], city_id=10))
