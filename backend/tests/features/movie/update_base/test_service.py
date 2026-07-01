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


def test_update_base_uses_shared_maoyan_client(monkeypatch: MonkeyPatch) -> None:
    service = UpdateBaseService()
    calls: list[tuple[str, str, int]] = []

    def fake_maoyan_get_text(url: str, purpose: str, city_id: int, **_: object) -> str:
        calls.append((url, purpose, city_id))
        return _FakeResponse.text

    monkeypatch.setattr(base_module, "maoyan_get_text", fake_maoyan_get_text)

    result = service._fetch_page(show_type=1, page=1, city_id=10)

    assert result is not None
    movies, is_expected_empty = result
    assert is_expected_empty is False
    assert [(movie.id, movie.title) for movie in movies] == [(1522535, "Magic Girl")]
    assert calls == [("https://www.maoyan.com/films?showType=1", "获取电影列表", 10)]


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
