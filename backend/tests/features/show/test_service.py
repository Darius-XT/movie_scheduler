# pyright: reportPrivateUsage=false
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pytest import MonkeyPatch

import movie_scheduler.features.show.service as show_module
from movie_scheduler.core.exceptions import MaoyanVerificationError
from movie_scheduler.features.show.service import ShowService


@pytest.mark.parametrize("movie_id", [1, 2, -4, 999])
def test_single_movie_stream_limits_fetch_and_validates_selection(monkeypatch: MonkeyPatch, movie_id: int) -> None:
    service = ShowService()
    monkeypatch.setattr(service, "_list_cinema_movie_ids", lambda: [1, 3])
    fetch = AsyncMock(return_value=[])
    persist = AsyncMock(return_value=show_module.ShowUpdateStats(0, 0, 0))
    latest = Mock(return_value=None)
    monkeypatch.setattr(service, "_fetch_shows_for_selected_movies", fetch)
    monkeypatch.setattr(service, "_persist_results", persist)
    monkeypatch.setattr(show_module.movie_repository, "get_latest_shows_updated_at", latest)

    async def collect() -> list[str]:
        return [frame async for frame in service.stream_show_update(10, movie_id=movie_id)]

    events = [json.loads(line[6:]) for frame in asyncio.run(collect()) for line in frame.splitlines()
              if line.startswith("data: ")]
    if movie_id == 1:
        fetch.assert_awaited_once_with([1], city_id=10)
        persist.assert_awaited_once_with([1], [])
        latest.assert_called_once_with([1])
        assert events[-1]["type"] == "complete"
    else:
        fetch.assert_not_awaited()
        persist.assert_not_awaited()
        assert events[-1]["type"] == "error"


def test_single_movie_stream_preserves_data_on_verification(monkeypatch: MonkeyPatch) -> None:
    service = ShowService()
    monkeypatch.setattr(service, "_list_cinema_movie_ids", lambda: [1])
    monkeypatch.setattr(service, "_fetch_shows_for_selected_movies", AsyncMock(side_effect=MaoyanVerificationError()))
    persist = AsyncMock()
    monkeypatch.setattr(service, "_persist_results", persist)

    async def collect() -> list[str]:
        return [frame async for frame in service.stream_show_update(10, movie_id=1)]

    frames = "".join(asyncio.run(collect()))
    assert '"error"' in frames
    assert '"complete"' not in frames
    persist.assert_not_awaited()


def test_batch_fetch_only_selects_cinema_movies(monkeypatch: MonkeyPatch) -> None:
    movies = [SimpleNamespace(id=mid, viewing_location=location) for mid, location in [
        (1, "cinema"), (2, "home"), (3, None), (-4, "cinema"),
    ]]
    monkeypatch.setattr(show_module.movie_repository, "list_wished_movies", Mock(return_value=movies))
    service = ShowService()
    fetch = AsyncMock(return_value=[])
    persist = AsyncMock(return_value=show_module.ShowUpdateStats(0, 0, 0))
    monkeypatch.setattr(service, "_fetch_shows_for_selected_movies", fetch)
    monkeypatch.setattr(service, "_persist_results", persist)
    asyncio.run(service.refresh_wished_movie_shows(10))
    fetch.assert_awaited_once_with([1], city_id=10)
    persist.assert_awaited_once_with([1], [])


@pytest.mark.parametrize("location", ["home", None])
def test_single_fetch_skips_non_cinema_movies(monkeypatch: MonkeyPatch, location: str | None) -> None:
    movie = SimpleNamespace(id=1, is_wished=True, viewing_location=location)
    monkeypatch.setattr(show_module.movie_repository, "get_movie_by_id", Mock(return_value=movie))
    service = ShowService()
    fetch = AsyncMock()
    delete = Mock()
    monkeypatch.setattr(service, "_fetch_shows_for_selected_movies", fetch)
    monkeypatch.setattr(show_module.movie_show_repository, "delete_for_movie", delete)
    assert asyncio.run(service.refresh_movie_shows(1, 10)) == 0
    fetch.assert_not_called()
    delete.assert_not_called()


@pytest.mark.parametrize("failed_stage", ["dates", "cinemas", "shows", "empty_cinemas"])
def test_failed_fetch_preserves_shows_and_timestamp(monkeypatch: MonkeyPatch, failed_stage: str) -> None:
    service = ShowService()
    movie = SimpleNamespace(id=1490532, title="玩具总动员5", is_wished=True, viewing_location="cinema")
    writes: list[str] = []
    def get_movie(movie_id: int) -> SimpleNamespace:
        return movie

    def write(*args: object) -> None:
        writes.append("write")

    monkeypatch.setattr(show_module.movie_repository, "list_wished_movies", lambda: [movie])
    monkeypatch.setattr(show_module.movie_repository, "get_movie_by_id", get_movie)
    monkeypatch.setattr(show_module.movie_show_repository, "replace_for_movie", write)
    monkeypatch.setattr(show_module.movie_repository, "touch_shows_updated_at", write)

    def fetch(url: str, label: str, city_id: int, **kwargs: object) -> str | None:
        if url == "https://www.maoyan.com/":
            return "<html></html>"
        if "/cinema/" in url:
            return None if failed_stage == "shows" else _MAOYAN_CINEMA_HTML
        if "showDate=" in url:
            if failed_stage == "empty_cinemas":
                return "<html><body>页面暂不可用</body></html>"
            return None if failed_stage == "cinemas" else _MAOYAN_MOVIE_DATE_CINEMAS_HTML
        return None if failed_stage == "dates" else _MAOYAN_MOVIE_CINEMAS_HTML

    monkeypatch.setattr(show_module, "_http_get_text", fetch)
    with pytest.raises(show_module.ExternalDependencyError, match="已保留原有场次"):
        asyncio.run(service.refresh_wished_movie_shows(10))
    assert writes == []


@pytest.mark.parametrize("blocked_stage", ["home", "dates", "cinemas", "shows"])
def test_verification_reports_stop_and_preserves_shows(monkeypatch: MonkeyPatch, blocked_stage: str) -> None:
    movie = SimpleNamespace(id=1490532, title="玩具总动员5", is_wished=True, viewing_location="cinema")
    replace = Mock()
    touch = Mock()
    monkeypatch.setattr(show_module.movie_repository, "list_wished_movies", lambda: [movie])
    monkeypatch.setattr(show_module.movie_repository, "get_movie_by_id", Mock(return_value=movie))
    monkeypatch.setattr(show_module.movie_show_repository, "replace_for_movie", replace)
    monkeypatch.setattr(show_module.movie_repository, "touch_shows_updated_at", touch)

    def fetch(url: str, label: str, city_id: int, **kwargs: object) -> str:
        if url == "https://www.maoyan.com/":
            stage, content = "home", "<html></html>"
        elif "/cinema/" in url:
            stage, content = "shows", _MAOYAN_CINEMA_HTML
        elif "showDate=" in url:
            stage, content = "cinemas", _MAOYAN_MOVIE_DATE_CINEMAS_HTML
        else:
            stage, content = "dates", _MAOYAN_MOVIE_CINEMAS_HTML
        if stage == blocked_stage:
            raise MaoyanVerificationError()
        return content

    monkeypatch.setattr(show_module, "_http_get_text", fetch)

    async def collect() -> list[str]:
        return [frame async for frame in ShowService().stream_show_update(10)]

    frames = asyncio.run(collect())
    assert any('"type":"error"' in frame and "已停止本轮剩余抓取" in frame and "原有场次已保留" in frame for frame in frames)
    assert not any('"type":"complete"' in frame for frame in frames)
    replace.assert_not_called()
    touch.assert_not_called()


def test_verification_does_not_persist_other_movies_partial_results(monkeypatch: MonkeyPatch) -> None:
    service = ShowService()
    movies = [SimpleNamespace(id=i, is_wished=True, viewing_location="cinema") for i in [1, 2]]
    replace = Mock()
    touch = Mock()

    async def fetch_movie(movie_id: int, city_id: int) -> show_module._FinalMovieShowData:
        if movie_id == 1:
            raise MaoyanVerificationError()
        return show_module._FinalMovieShowData(movie_id, [])

    monkeypatch.setattr(show_module.movie_repository, "list_wished_movies", lambda: movies)
    monkeypatch.setattr(service, "_process_single_movie", fetch_movie)
    monkeypatch.setattr(show_module.movie_show_repository, "replace_for_movie", replace)
    monkeypatch.setattr(show_module.movie_repository, "touch_shows_updated_at", touch)
    with pytest.raises(MaoyanVerificationError):
        asyncio.run(service.refresh_wished_movie_shows(10))
    replace.assert_not_called()
    touch.assert_not_called()


def test_partial_failure_does_not_replace_failed_movie(monkeypatch: MonkeyPatch) -> None:
    service = ShowService()
    touched: list[int] = []
    replaced: list[int] = []
    async def wished(movie_id: int) -> bool:
        return True

    def replace(movie_id: int, shows: list[object]) -> None:
        replaced.append(movie_id)

    def existing(movie_ids: list[int]) -> list[object]:
        return []

    monkeypatch.setattr(service, "_is_movie_wished", wished)
    monkeypatch.setattr(show_module.movie_show_repository, "list_for_movies", existing)
    monkeypatch.setattr(show_module.movie_show_repository, "replace_for_movie", replace)
    monkeypatch.setattr(show_module.movie_repository, "touch_shows_updated_at", touched.append)
    result = asyncio.run(service._persist_results([1, 2], [show_module._FinalMovieShowData(1, [])]))
    assert result.failed_movies == 1
    assert touched == replaced == [1]


def test_manual_movies_do_not_trigger_show_fetching(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(show_module.movie_repository, "list_wished_movies", lambda: [
        SimpleNamespace(id=-123, is_wished=True),
    ])
    service = ShowService()
    assert asyncio.run(service.refresh_movie_shows(-123)) == 0
    stats = asyncio.run(service.refresh_wished_movie_shows(city_id=10))
    assert stats.movies_with_shows == 0


def test_http_get_text_delegates_to_shared_maoyan_client_without_logging_cookie(monkeypatch: MonkeyPatch) -> None:
    messages: list[str] = []
    calls: list[tuple[str, str, int, dict[str, object]]] = []

    def fake_debug(message: str, *args: object) -> None:
        messages.append(message % args)

    def fake_maoyan_get_text(url: str, purpose: str, city_id: int, **kwargs: object) -> str:
        calls.append((url, purpose, city_id, kwargs))
        return "<html></html>"

    monkeypatch.setattr(show_module.logger, "debug", fake_debug)
    monkeypatch.setattr(show_module, "maoyan_get_text", fake_maoyan_get_text)

    result = show_module._http_get_text(
        "https://www.maoyan.com/cinema/169",
        "获取影院场次页面",
        10,
        hot_movie_ids=[1490532],
    )

    log_text = "\n".join(messages)
    assert result == "<html></html>"
    assert "Cookie" not in log_text
    assert calls == [(
        "https://www.maoyan.com/cinema/169",
        "获取影院场次页面",
        10,
        {"hot_movie_ids": [1490532], "timeout": 30, "verify": False},
    )]


def test_refresh_movie_shows_parses_maoyan_cinema_html(monkeypatch: MonkeyPatch) -> None:
    service = ShowService()
    captured_shows: list[dict[str, object]] = []
    captured_movie_hot_ids: list[list[int] | None] = []
    captured_cinema_hot_ids: list[list[int] | None] = []
    movie = SimpleNamespace(id=1490532, title="玩具总动员5", is_wished=True, viewing_location="cinema")

    def fake_get_movie_by_id(movie_id: int) -> SimpleNamespace | None:
        return movie if movie_id == 1490532 else None

    def fake_http_get_text(
        url: str,
        log_label: str,
        city_id: int,
        *,
        hot_movie_ids: list[int] | None = None,
    ) -> str | None:
        assert city_id == 10
        if url == "https://www.maoyan.com/":
            return '<a href="/cinemas?movieId=1366168" data-val="{movieid:1366168}">ticket</a>'
        if url == "https://www.maoyan.com/cinemas?movieId=1490532":
            captured_movie_hot_ids.append(hot_movie_ids)
            return _MAOYAN_MOVIE_CINEMAS_HTML
        if url == "https://www.maoyan.com/cinemas?movieId=1490532&showDate=2026-06-23":
            captured_movie_hot_ids.append(hot_movie_ids)
            return _MAOYAN_MOVIE_DATE_CINEMAS_HTML
        if url == "https://www.maoyan.com/cinema/38931":
            captured_cinema_hot_ids.append(hot_movie_ids)
            return _MAOYAN_CINEMA_HTML
        return None

    def fake_replace_for_movie(movie_id: int, shows: list[dict[str, object]]) -> int:
        captured_shows.extend(shows)
        return len(shows)

    def fake_touch_shows_updated_at(movie_id: int) -> bool:
        return True

    def fake_list_for_movies(movie_ids: list[int]) -> list[object]:
        return []

    monkeypatch.setattr(show_module.config_manager, "maoyan_cookie", (
        "uuid_n_v=v1; hotMovieIds=1,2; old-moviepage-ci=1; ci=1126; global-guide-isclose=true"
    ))
    monkeypatch.setattr(show_module.movie_repository, "get_movie_by_id", fake_get_movie_by_id)
    monkeypatch.setattr(show_module.movie_repository, "touch_shows_updated_at", fake_touch_shows_updated_at)
    monkeypatch.setattr(show_module.movie_show_repository, "list_for_movies", fake_list_for_movies)
    monkeypatch.setattr(show_module.movie_show_repository, "replace_for_movie", fake_replace_for_movie)
    monkeypatch.setattr(show_module, "_http_get_text", fake_http_get_text)

    result = asyncio.run(service.refresh_movie_shows(1490532, city_id=10))

    assert result == 1
    assert captured_shows == [{
        "movie_id": 1490532,
        "cinema_id": 38931,
        "cinema_name": "Imagine Box 响像力影城",
        "date": "2026-06-23",
        "time": "10:00",
        "price": "39.9",
    }]
    assert captured_movie_hot_ids[0] == [1490532, 1366168]
    assert captured_cinema_hot_ids[0] == [1490532, 1366168]


def test_hot_movie_ids_cache_expires_after_one_hour(monkeypatch: MonkeyPatch) -> None:
    service = ShowService()
    now = 1_000.0
    calls: list[str] = []

    def fake_monotonic() -> float:
        return now

    def fake_http_get_text(
        url: str,
        log_label: str,
        city_id: int,
        *,
        hot_movie_ids: list[int] | None = None,
    ) -> str | None:
        assert city_id == 10
        assert hot_movie_ids is None
        calls.append(url)
        movie_id = 11 if len(calls) == 1 else 22
        return f'<a href="/cinemas?movieId={movie_id}" data-val="{{movieid:{movie_id}}}">ticket</a>'

    monkeypatch.setattr(show_module, "monotonic", fake_monotonic)
    monkeypatch.setattr(show_module, "_http_get_text", fake_http_get_text)
    monkeypatch.setattr(show_module.config_manager, "maoyan_cookie", "hotMovieIds=1,2; old-moviepage-ci=1")

    assert service._get_hot_movie_ids(10) == [11]
    now = 1_000.0 + 3_599
    assert service._get_hot_movie_ids(10) == [11]
    now = 1_000.0 + 3_601
    assert service._get_hot_movie_ids(10) == [22]
    assert calls == ["https://www.maoyan.com/", "https://www.maoyan.com/"]


def test_persist_results_deduplicates_show_rows(monkeypatch: MonkeyPatch) -> None:
    service = ShowService()
    captured_shows: list[dict[str, object]] = []

    async def fake_is_movie_wished(movie_id: int) -> bool:
        return movie_id == 1490532

    def fake_replace_for_movie(movie_id: int, shows: list[dict[str, object]]) -> int:
        captured_shows.extend(shows)
        return len(shows)

    def fake_list_for_movies(movie_ids: list[int]) -> list[object]:
        return []

    def fake_touch_shows_updated_at(movie_id: int) -> bool:
        return True

    monkeypatch.setattr(service, "_is_movie_wished", fake_is_movie_wished)
    monkeypatch.setattr(show_module.movie_show_repository, "list_for_movies", fake_list_for_movies)
    monkeypatch.setattr(show_module.movie_show_repository, "replace_for_movie", fake_replace_for_movie)
    monkeypatch.setattr(show_module.movie_repository, "touch_shows_updated_at", fake_touch_shows_updated_at)

    result = asyncio.run(service._persist_results(
        [1490532],
        [
            show_module._FinalMovieShowData(
                movie_id=1490532,
                cinemas=[
                    show_module._CinemaShowData(
                        cinema_id=38931,
                        cinema_name="Imagine Box",
                        shows=[
                            show_module._ShowItem(date="2026-06-23", time="10:00", price="0"),
                            show_module._ShowItem(date="2026-06-23", time="10:00", price="39.9"),
                        ],
                    ),
                ],
            ),
        ],
    ))

    assert result.added == 1
    assert result.movies_with_shows == 1
    assert captured_shows == [{
        "movie_id": 1490532,
        "cinema_id": 38931,
        "cinema_name": "Imagine Box",
        "date": "2026-06-23",
        "time": "10:00",
        "price": "39.9",
    }]


_MAOYAN_MOVIE_CINEMAS_HTML = """
<html>
  <body>
    <div class="tags">
      <a data-val="{TagName:'2026-06-23'}" href="?movieId=1490532&amp;showDate=2026-06-23">今天 6月23</a>
    </div>
  </body>
</html>
"""


_MAOYAN_MOVIE_DATE_CINEMAS_HTML = """
<html>
  <body>
    <div class="cinema-cell">
      <a class="cinema-name" href="/cinema/38931?movieId=1490532" data-val="{city_id: 10, cinema_id: 38931}">
        Imagine Box 响像力影城
      </a>
    </div>
    <div class="cinema-pager"></div>
  </body>
</html>
"""


_MAOYAN_CINEMA_HTML = """
<!DOCTYPE html>
<html>
  <head>
    <title>Imagine Box 响像力影城_选座购票_影院地址电话_优惠服务-猫眼电影</title>
  </head>
  <body>
    <div class="cinema-brief-container">
      <h3 class="name text-ellipsis">Imagine Box 响像力影城</h3>
    </div>
    <div class="show-list">
      <div class="movie-info">
        <span class="name">玩具总动员5</span>
      </div>
      <div class="date-list">
        <span class="date-item active" data-index="0">今天 6月23</span>
      </div>
      <div class="plist-container active">
        <table class="plist">
          <tbody>
            <tr>
              <td>
                <span class="begin-time">10:00</span>
                <span class="end-time">11:42散场</span>
              </td>
              <td>英语 3D</td>
              <td>1号厅</td>
              <td><span class="sell-price">39.9</span></td>
              <td>
                <a href="/xseats/202606230001012?movieId=1490532&amp;cinemaId=38931"
                   data-val="{movie_id: 1490532, cinema_id:38931}">选座购票</a>
              </td>
            </tr>
            <tr>
              <td><span class="begin-time">12:30</span></td>
              <td>国语 2D</td>
              <td>2号厅</td>
              <td><span class="sell-price">29.9</span></td>
              <td>
                <a href="/xseats/202606230001099?movieId=1366168&amp;cinemaId=38931"
                   data-val="{movie_id: 1366168, cinema_id:38931}">选座购票</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </body>
</html>
"""
