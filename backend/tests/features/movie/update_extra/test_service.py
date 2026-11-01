from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch

import movie_scheduler.features.movie.update_extra.service as extra_module
from movie_scheduler.core.exceptions import MaoyanVerificationError
from movie_scheduler.features.movie.update_extra.service import UpdateExtraService


def test_details_refresh_skips_manual_movies(monkeypatch: MonkeyPatch) -> None:
    fetch = Mock(side_effect=AssertionError("手动电影不应发起猫眼请求"))
    monkeypatch.setattr(extra_module.movie_repository, "get_all_movies", lambda: [
        SimpleNamespace(id=-123, title="手动电影"),
    ])
    monkeypatch.setattr(extra_module, "maoyan_get_text", fetch)
    assert asyncio.run(UpdateExtraService().update_all()) == 0
    fetch.assert_not_called()


_MOVIE_DETAIL_HTML = """
    <html>
      <body>
        <script>
          window.__DATA__ = {
            "movie": {
              "id": 1522535,
              "dir": "New Director",
              "dra": "New description",
              "dur": 107,
              "oriLang": "English",
              "src": "France"
            }
          };
        </script>
      </body>
    </html>
    """


def test_update_extra_fills_missing_existing_movie_details(monkeypatch: MonkeyPatch) -> None:
    service = UpdateExtraService()
    saved: list[dict[str, object]] = []
    movie = SimpleNamespace(
        id=1522535,
        title="Normandie",
        director="Old Director",
        country=None,
        language="Old Language",
        duration="110min",
        description="Old description",
    )

    def fake_get_all_movies() -> list[object]:
        return [movie]

    def fake_save_movie(row: dict[str, object]) -> bool:
        saved.append(row)
        return True

    def fake_maoyan_get_text(url: str, purpose: str, city_id: int, **kwargs: object) -> str:
        assert url == "https://www.maoyan.com/films/1522535"
        assert purpose == "获取电影详情页面"
        assert kwargs["headers_profile"] == "mobile"
        assert kwargs["hot_movie_ids"] == [1522535]
        return _MOVIE_DETAIL_HTML

    monkeypatch.setattr(extra_module.movie_repository, "get_all_movies", fake_get_all_movies)
    monkeypatch.setattr(extra_module.movie_repository, "save_movie", fake_save_movie)
    monkeypatch.setattr(extra_module, "maoyan_get_text", fake_maoyan_get_text)

    result = asyncio.run(service.update_all())

    assert result == 1
    assert saved == [{
        "id": 1522535,
        "director": "New Director",
        "country": "France",
        "language": "English",
        "duration": "107min",
        "description": "New description",
    }]


def test_update_extra_skips_complete_details_without_requesting(monkeypatch: MonkeyPatch) -> None:
    service = UpdateExtraService()
    saved: list[dict[str, object]] = []
    movie = SimpleNamespace(
        id=1522535,
        title="Normandie",
        director="New Director",
        country="France",
        language="English",
        duration="107min",
        description="New description",
    )

    def fake_get_all_movies() -> list[object]:
        return [movie]

    def fake_save_movie(row: dict[str, object]) -> bool:
        saved.append(row)
        return True

    def fake_maoyan_get_text(url: str, purpose: str, city_id: int, **kwargs: object) -> str:
        raise AssertionError("已有完整详情不应重复请求")

    monkeypatch.setattr(extra_module.movie_repository, "get_all_movies", fake_get_all_movies)
    monkeypatch.setattr(extra_module.movie_repository, "save_movie", fake_save_movie)
    monkeypatch.setattr(extra_module, "maoyan_get_text", fake_maoyan_get_text)

    result = asyncio.run(service.update_all())

    assert result == 0
    assert saved == []


@pytest.mark.parametrize("field", ["director", "country", "language", "duration", "description"])
@pytest.mark.parametrize("missing", [None, "  ", "暂无资料"])
def test_update_extra_fetches_empty_or_placeholder_fields(monkeypatch: MonkeyPatch, field: str, missing: str | None) -> None:
    movie = SimpleNamespace(id=1522535, title="电影", director="导演", country="国家", language="语言",
                            duration="100min", description="简介")
    setattr(movie, field, missing)
    fetch = Mock(return_value=_MOVIE_DETAIL_HTML)
    save = Mock(return_value=True)
    monkeypatch.setattr(extra_module.movie_repository, "get_all_movies", lambda: [movie])
    monkeypatch.setattr(extra_module.movie_repository, "save_movie", save)
    monkeypatch.setattr(extra_module, "maoyan_get_text", fetch)
    assert asyncio.run(UpdateExtraService().update_all()) == 1
    fetch.assert_called_once()
    save.assert_called_once()


def test_update_extra_stops_before_requesting_remaining_movies(monkeypatch: MonkeyPatch) -> None:
    complete = SimpleNamespace(id=4, title="完整电影", director="导演", country="国家", language="语言",
                               duration="100min", description="简介")
    movies = [SimpleNamespace(id=i, title=f"电影 {i}") for i in [1, 2, 3, -1]] + [complete]
    fetch = Mock(side_effect=[_MOVIE_DETAIL_HTML, MaoyanVerificationError(), _MOVIE_DETAIL_HTML])
    save = Mock(return_value=True)
    events: list[extra_module.UpdateBaseProgressEvent] = []
    monkeypatch.setattr(extra_module.movie_repository, "get_all_movies", lambda: movies)
    monkeypatch.setattr(extra_module.movie_repository, "save_movie", save)
    monkeypatch.setattr(extra_module, "maoyan_get_text", fetch)
    with pytest.raises(MaoyanVerificationError):
        asyncio.run(UpdateExtraService().update_all(events.append))
    assert [call.args[0] for call in fetch.call_args_list] == [
        "https://www.maoyan.com/films/1", "https://www.maoyan.com/films/2",
    ]
    assert [(event.current, event.total) for event in events] == [(0, 3), (1, 3), (1, 3)]
    save.assert_called_once()
    assert save.call_args.args[0]["id"] == 1


def test_update_extra_continues_after_ordinary_failure(monkeypatch: MonkeyPatch) -> None:
    fetch = Mock(side_effect=[None, _MOVIE_DETAIL_HTML])
    save = Mock(return_value=True)
    monkeypatch.setattr(extra_module.movie_repository, "get_all_movies", lambda: [
        SimpleNamespace(id=1, title="暂时失败"), SimpleNamespace(id=2, title="继续补齐"),
    ])
    monkeypatch.setattr(extra_module.movie_repository, "save_movie", save)
    monkeypatch.setattr(extra_module, "maoyan_get_text", fetch)
    assert asyncio.run(UpdateExtraService().update_all()) == 1
    assert fetch.call_count == 2
    assert save.call_args.args[0]["id"] == 2


def test_update_extra_does_not_save_unchanged_placeholders(monkeypatch: MonkeyPatch) -> None:
    movie = SimpleNamespace(id=1, title="未公布详情", director="暂无导演", country="暂无国家", language="暂无语言",
                            duration="暂无时长", description="暂无简介")
    fetch = Mock(return_value='<script>{"movie":{"id":1}}</script>')
    save = Mock()
    monkeypatch.setattr(extra_module.movie_repository, "get_all_movies", lambda: [movie])
    monkeypatch.setattr(extra_module.movie_repository, "save_movie", save)
    monkeypatch.setattr(extra_module, "maoyan_get_text", fetch)
    assert asyncio.run(UpdateExtraService().update_all()) == 0
    fetch.assert_called_once()
    save.assert_not_called()
