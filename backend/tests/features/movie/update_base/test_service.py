# pyright: reportPrivateUsage=false
from __future__ import annotations

from pytest import MonkeyPatch

import movie_scheduler.features.movie.update_base.service as base_module
from movie_scheduler.features.movie.update_base.service import UpdateBaseService


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


class _FakeSession:
    def __init__(self) -> None:
        self.cookies: dict[str, str] = {}
        self.requests: list[tuple[str, dict[str, str]]] = []

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        **_: object,
    ) -> _FakeResponse:
        self.requests.append((url, headers or {}))
        return _FakeResponse()


def test_update_base_uses_configured_maoyan_cookie(monkeypatch: MonkeyPatch) -> None:
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
        "https://www.maoyan.com/films?showType=1&offset=0",
        "https://www.maoyan.com/films?showType=1&offset=0",
    ]
    assert "old-moviepage-ci=10" in fake_session.requests[-1][1]["Cookie"]
    assert "hotMovieIds=1,2" in fake_session.requests[-1][1]["Cookie"]


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
