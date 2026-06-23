from __future__ import annotations

import asyncio
from types import SimpleNamespace

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


def test_update_extra_updates_changed_existing_movie_details(monkeypatch) -> None:
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

    monkeypatch.setattr(extra_module.movie_repository, "get_all_movies", lambda: [movie])
    monkeypatch.setattr(extra_module.movie_repository, "save_movie", lambda row: saved.append(row) or True)
    monkeypatch.setattr(extra_module.requests, "get", lambda *args, **kwargs: _FakeResponse())

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


def test_update_extra_skips_unchanged_movie_details(monkeypatch) -> None:
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

    monkeypatch.setattr(extra_module.movie_repository, "get_all_movies", lambda: [movie])
    monkeypatch.setattr(extra_module.movie_repository, "save_movie", lambda row: saved.append(row) or True)
    monkeypatch.setattr(extra_module.requests, "get", lambda *args, **kwargs: _FakeResponse())

    result = asyncio.run(service.update_all())

    assert result == 0
    assert saved == []
