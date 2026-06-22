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
              "dir": "白雪",
              "dra": "文牧野监制、白雪执导。",
              "dur": 107,
              "oriLang": "国语",
              "src": "中国大陆"
            }
          };
        </script>
      </body>
    </html>
    """


def test_update_extra_parses_maoyan_mobile_movie_page(monkeypatch) -> None:
    service = UpdateExtraService()
    saved: list[dict[str, object]] = []
    movie = SimpleNamespace(id=1522535, title="魔方小姐")

    def fake_save_movie(row: dict[str, object]) -> bool:
        saved.append(row)
        return True

    monkeypatch.setattr(extra_module.movie_repository, "get_movies_without_details", lambda: [movie])
    monkeypatch.setattr(extra_module.movie_repository, "save_movie", fake_save_movie)
    monkeypatch.setattr(extra_module.requests, "get", lambda *args, **kwargs: _FakeResponse())

    result = asyncio.run(service.update_all())

    assert result == 1
    assert saved == [{
        "id": 1522535,
        "director": "白雪",
        "country": "中国大陆",
        "language": "国语",
        "duration": "107min",
        "description": "文牧野监制、白雪执导。",
    }]
