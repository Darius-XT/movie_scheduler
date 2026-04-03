"""场次结果组装器测试。"""

from dataclasses import asdict

from app.use_cases.show_fetching.models import FetchedShowItem
from app.use_cases.show_fetching.result_builder import MovieShowDataBuilder


def test_builder_merges_show_rows_into_cinemas() -> None:
    """同一影院的多条场次应合并到一个影院节点下。"""
    builder = MovieShowDataBuilder()
    movie_data = builder.create_movie_data(1, "测试电影")

    builder.merge_shows(
        movie_data,
        [
            FetchedShowItem(
                movie_id=1,
                movie_name="测试电影",
                cinema_id=10,
                cinema_name="影院A",
                show_date="2026-04-05",
                show_time="18:00",
                price="30",
            ),
            FetchedShowItem(
                movie_id=1,
                movie_name="测试电影",
                cinema_id=10,
                cinema_name="影院A",
                show_date="2026-04-05",
                show_time="20:00",
                price="35",
            ),
        ],
    )

    result = builder.finalize_movie_data(movie_data)
    payload = asdict(result)

    assert len(payload["cinemas"]) == 1
    assert payload["cinemas"][0]["cinema_id"] == 10
    assert payload["cinemas"][0]["shows"] == [
        {"date": "2026-04-05", "time": "18:00", "price": "30"},
        {"date": "2026-04-05", "time": "20:00", "price": "35"},
    ]


def test_builder_builds_cinemas_from_async_results() -> None:
    """异步抓取结果应按影院重新聚合。"""
    builder = MovieShowDataBuilder()

    cinemas = builder.build_cinemas_from_shows(
        [
            [
                FetchedShowItem(
                    movie_id=1,
                    movie_name="测试电影",
                    cinema_id=10,
                    cinema_name="影院A",
                    show_date="2026-04-05",
                    show_time="18:00",
                    price="30",
                )
            ],
            [
                FetchedShowItem(
                    movie_id=1,
                    movie_name="测试电影",
                    cinema_id=20,
                    cinema_name="影院B",
                    show_date="2026-04-06",
                    show_time="19:00",
                    price="40",
                )
            ],
        ]
    )

    assert asdict(builder.finalize_movie_data(builder.create_movie_data(1, "测试电影"))) is not None

    assert {cinema_id: asdict(cinema) for cinema_id, cinema in cinemas.items()} == {
        10: {
            "cinema_id": 10,
            "cinema_name": "影院A",
            "shows": [{"date": "2026-04-05", "time": "18:00", "price": "30"}],
        },
        20: {
            "cinema_id": 20,
            "cinema_name": "影院B",
            "shows": [{"date": "2026-04-06", "time": "19:00", "price": "40"}],
        },
    }
