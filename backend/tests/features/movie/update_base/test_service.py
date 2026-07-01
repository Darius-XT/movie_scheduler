# pyright: reportPrivateUsage=false
from __future__ import annotations

from pytest import MonkeyPatch

import movie_scheduler.features.movie.update_base.service as base_module
from movie_scheduler.features.movie.update_base.service import UpdateBaseService, _ScrapedMovieBaseInfo


class _FakeResponse:
    status_code = 200
    text = """
    <html>
      <body>
        <dl class="movie-list">
          <dd>
            <a href="/films/1522535"></a>
            <div class="movie-item-title"><a>Magic Girl</a></div>
          </dd>
        </dl>
      </body>
    </html>
    """


class _FakeCookieJar:
    def __init__(self) -> None:
        self.values: dict[str, tuple[str, str | None, str | None]] = {}

    def clear(self) -> None:
        self.values.clear()

    def set(
        self,
        name: str,
        value: str,
        *,
        domain: str | None = None,
        path: str | None = None,
    ) -> None:
        self.values[name] = (value, domain, path)


class _FakePreparedRequest:
    def __init__(self, url: str, headers: dict[str, str]) -> None:
        self.url = url
        self.headers = headers


class _FakeSession:
    def __init__(self) -> None:
        self.cookies = _FakeCookieJar()
        self.requests: list[tuple[str, dict[str, str]]] = []

    def prepare_request(self, request: base_module.requests.Request) -> _FakePreparedRequest:
        url = request.url or ""
        headers = dict(request.headers or {})
        cookie = "; ".join(f"{name}={value}" for name, (value, _domain, _path) in self.cookies.values.items())
        if cookie and "Cookie" not in headers:
            headers["Cookie"] = cookie
        return _FakePreparedRequest(url, headers)

    def send(
        self,
        prepared_request: _FakePreparedRequest,
        **_: object,
    ) -> _FakeResponse:
        self.requests.append((prepared_request.url, prepared_request.headers))
        return _FakeResponse()


def test_update_base_seeds_maoyan_cookie_without_stale_hot_movie_ids(monkeypatch: MonkeyPatch) -> None:
    service = UpdateBaseService()
    fake_session = _FakeSession()
    service.session = fake_session  # type: ignore[assignment]

    monkeypatch.setattr(
        base_module.config_manager,
        "maoyan_cookie",
        "uuid_n_v=v1; hotMovieIds=1,2; old-moviepage-ci=1; global-guide-isclose=true",
    )

    result = service._fetch_page(show_type=1, page=1, city_id=10)

    assert result is not None
    movies, is_expected_empty = result
    assert is_expected_empty is False
    assert [(movie.id, movie.title) for movie in movies] == [(1522535, "Magic Girl")]
    assert [url for url, _headers in fake_session.requests] == [
        "https://www.maoyan.com/films?showType=1",
        "https://www.maoyan.com/films?showType=1",
    ]
    assert "Cookie" in fake_session.requests[-1][1]
    assert "hotMovieIds=" not in fake_session.requests[-1][1]["Cookie"]
    assert "old-moviepage-ci=10" in fake_session.requests[-1][1]["Cookie"]
    assert "ci=10" in fake_session.requests[-1][1]["Cookie"]
    assert fake_session.cookies.values["old-moviepage-ci"][0] == "10"
    assert fake_session.cookies.values["ci"][0] == "10"
    assert "hotMovieIds" not in fake_session.cookies.values


def test_movie_list_url_omits_offset_on_first_page() -> None:
    service = UpdateBaseService()

    assert service._movie_list_url(show_type=1, page=1) == "https://www.maoyan.com/films?showType=1"
    assert service._movie_list_url(show_type=1, page=2) == "https://www.maoyan.com/films?showType=1&offset=18"


def test_update_base_skips_stale_deletes_when_scrape_is_incomplete(monkeypatch: MonkeyPatch) -> None:
    service = UpdateBaseService()
    deleted_ids: list[int] = []

    def fake_get_movies_count() -> int:
        return 2

    def fake_delete_movie(movie_id: int) -> bool:
        deleted_ids.append(movie_id)
        return True

    monkeypatch.setattr(base_module.movie_repository, "get_movies_count", fake_get_movies_count)
    monkeypatch.setattr(base_module.movie_repository, "delete_movie", fake_delete_movie)

    result = service._perform_incremental_update({1, 2}, [], remove_stale=False)

    assert result.removed == 0
    assert result.total == 2
    assert deleted_ids == []


def test_scrape_one_type_logs_duplicate_details(monkeypatch: MonkeyPatch) -> None:
    service = UpdateBaseService()
    info_messages: list[str] = []
    debug_messages: list[str] = []

    def fake_fetch_page(
        show_type: int,
        page: int,
        city_id: int,
    ) -> tuple[list[_ScrapedMovieBaseInfo], bool]:
        if page == 1:
            return [
                _ScrapedMovieBaseInfo(id=1, title="Movie A", genres="", actors=""),
                _ScrapedMovieBaseInfo(id=2, title="Movie B", genres="", actors=""),
            ], False
        if page == 2:
            return [
                _ScrapedMovieBaseInfo(id=1, title="Movie A", genres="", actors=""),
                _ScrapedMovieBaseInfo(id=3, title="Movie C", genres="", actors=""),
                _ScrapedMovieBaseInfo(id=1, title="Movie A", genres="", actors=""),
            ], False
        return [], True

    def record_info(message: str, *args: object) -> None:
        info_messages.append(message % args)

    def record_debug(message: str, *args: object) -> None:
        debug_messages.append(message % args)

    monkeypatch.setattr(service, "_fetch_page", fake_fetch_page)
    monkeypatch.setattr(base_module.logger, "info", record_info)
    monkeypatch.setattr(base_module.logger, "debug", record_debug)

    movies, succeeded = service._scrape_one_type(1, "正在热映", 10, None)

    assert succeeded is True
    assert [movie.id for movie in movies] == [1, 2, 1, 3, 1]
    assert info_messages[-1] == "正在热映 列表抓取完成, 共抓取 5 部电影, 重复 2 部, 有效 3 部"
    assert any(
        "第 2 页第 1 个电影与第 1 页第 1 个电影重复, 电影名=Movie A, 电影ID=1" in message
        for message in debug_messages
    )
    assert any(
        "第 2 页第 3 个电影与第 1 页第 1 个电影重复, 电影名=Movie A, 电影ID=1" in message
        for message in debug_messages
    )
