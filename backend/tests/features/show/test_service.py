from __future__ import annotations

import asyncio
from types import SimpleNamespace

import movie_scheduler.features.show.service as show_module
from movie_scheduler.features.show.service import ShowService


def test_refresh_movie_shows_parses_maoyan_cinema_html(monkeypatch) -> None:
    service = ShowService()
    captured_shows: list[dict[str, object]] = []
    captured_movie_headers: list[dict[str, str]] = []
    captured_cinema_headers: list[dict[str, str]] = []
    movie = SimpleNamespace(id=1490532, title="玩具总动员5", is_wished=True)

    def fake_get_movie_by_id(movie_id: int) -> SimpleNamespace | None:
        return movie if movie_id == 1490532 else None

    def fake_http_get_text(
        url: str,
        log_label: str,
        headers: dict[str, str] | None = None,
    ) -> str | None:
        if url == "https://www.maoyan.com/":
            return '<a href="/cinemas?movieId=1366168" data-val="{movieid:1366168}">ticket</a>'
        if url == "https://www.maoyan.com/cinemas?movieId=1490532":
            captured_movie_headers.append(headers or {})
            return _MAOYAN_MOVIE_CINEMAS_HTML
        if url == "https://www.maoyan.com/cinemas?movieId=1490532&showDate=2026-06-23":
            captured_movie_headers.append(headers or {})
            return _MAOYAN_MOVIE_DATE_CINEMAS_HTML
        if url == "https://www.maoyan.com/cinema/38931":
            captured_cinema_headers.append(headers or {})
            return _MAOYAN_CINEMA_HTML
        return None

    def fake_replace_for_movie(movie_id: int, shows: list[dict[str, object]]) -> int:
        captured_shows.extend(shows)
        return len(shows)

    monkeypatch.setattr(show_module.config_manager, "maoyan_cookie", (
        "uuid_n_v=v1; hotMovieIds=1,2; old-moviepage-ci=1; global-guide-isclose=true"
    ))
    monkeypatch.setattr(show_module.movie_repository, "get_movie_by_id", fake_get_movie_by_id)
    monkeypatch.setattr(show_module.movie_repository, "touch_shows_updated_at", lambda movie_id: True)
    monkeypatch.setattr(show_module.movie_show_repository, "list_for_movies", lambda movie_ids: [])
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
    assert "hotMovieIds=1490532,1366168" in captured_movie_headers[0]["Cookie"]
    assert "hotMovieIds=1490532,1366168" in captured_cinema_headers[0]["Cookie"]
    assert "old-moviepage-ci=10" in captured_cinema_headers[0]["Cookie"]
    assert "; ci=" not in captured_cinema_headers[0]["Cookie"]
    assert not captured_cinema_headers[0]["Cookie"].startswith("ci=")


def test_hot_movie_ids_cache_expires_after_one_hour(monkeypatch) -> None:
    service = ShowService()
    now = 1_000.0
    calls: list[str] = []

    def fake_monotonic() -> float:
        return now

    def fake_http_get_text(
        url: str,
        log_label: str,
        headers: dict[str, str] | None = None,
    ) -> str | None:
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


def test_persist_results_deduplicates_show_rows(monkeypatch) -> None:
    service = ShowService()
    captured_shows: list[dict[str, object]] = []

    async def fake_is_movie_wished(movie_id: int) -> bool:
        return movie_id == 1490532

    def fake_replace_for_movie(movie_id: int, shows: list[dict[str, object]]) -> int:
        captured_shows.extend(shows)
        return len(shows)

    monkeypatch.setattr(service, "_is_movie_wished", fake_is_movie_wished)
    monkeypatch.setattr(show_module.movie_show_repository, "list_for_movies", lambda movie_ids: [])
    monkeypatch.setattr(show_module.movie_show_repository, "replace_for_movie", fake_replace_for_movie)
    monkeypatch.setattr(show_module.movie_repository, "touch_shows_updated_at", lambda movie_id: True)

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
