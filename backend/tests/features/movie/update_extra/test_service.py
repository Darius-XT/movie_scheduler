from __future__ import annotations

import asyncio
from types import SimpleNamespace

from pytest import MonkeyPatch

import movie_scheduler.features.movie.update_extra.service as extra_module
from movie_scheduler.features.movie.update_extra.service import UpdateExtraService


class _FakeResponse:
    status_code = 200
    text = """
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


def test_update_extra_updates_changed_existing_movie_details(monkeypatch: MonkeyPatch) -> None:
    service = UpdateExtraService()
    saved: list[dict[str, object]] = []
    movie = SimpleNamespace(
        id=1522535,
        title="Normandie",
        director="Old Director",
        country="Old Country",
        language="Old Language",
        duration="110min",
        description="Old description",
    )

    def fake_get_all_movies() -> list[object]:
        return [movie]

    def fake_save_movie(row: dict[str, object]) -> bool:
        saved.append(row)
        return True

    def fake_get(url: str, **kwargs: object) -> _FakeResponse:
        return _FakeResponse()

    monkeypatch.setattr(extra_module.movie_repository, "get_all_movies", fake_get_all_movies)
    monkeypatch.setattr(extra_module.movie_repository, "save_movie", fake_save_movie)
    monkeypatch.setattr(extra_module.requests, "get", fake_get)

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


def test_update_extra_skips_unchanged_movie_details(monkeypatch: MonkeyPatch) -> None:
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

    def fake_get(url: str, **kwargs: object) -> _FakeResponse:
        return _FakeResponse()

    monkeypatch.setattr(extra_module.movie_repository, "get_all_movies", fake_get_all_movies)
    monkeypatch.setattr(extra_module.movie_repository, "save_movie", fake_save_movie)
    monkeypatch.setattr(extra_module.requests, "get", fake_get)

    result = asyncio.run(service.update_all())

    assert result == 0
    assert saved == []
