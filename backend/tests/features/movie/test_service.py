import asyncio
from unittest.mock import Mock

from pytest import MonkeyPatch

from movie_scheduler.features.movie.models import Movie
from movie_scheduler.features.movie.repository import movie_repository
from movie_scheduler.features.movie.schemas import CreateManualMovieRequest
from movie_scheduler.features.movie.service import MovieService


def test_create_manual_movie_uses_local_id_and_wish_state(monkeypatch: MonkeyPatch) -> None:
    create = Mock(side_effect=Movie.from_dict)
    monkeypatch.setattr(movie_repository, "create_manual_movie", create)
    result = asyncio.run(MovieService().create_manual_movie(CreateManualMovieRequest(title=" 手动电影 ")))
    data = create.call_args.args[0]
    assert -(2**52) <= data["id"] < 0
    assert data["title"] == "手动电影"
    assert result["is_wished"] is True
