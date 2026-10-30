import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from pytest import MonkeyPatch

from movie_scheduler.features.movie.models import Movie
from movie_scheduler.features.movie.repository import movie_repository
from movie_scheduler.features.movie.schemas import CreateManualMovieRequest, SetMovieLabelRequest
from movie_scheduler.features.movie.service import MovieService
from movie_scheduler.core.exceptions import AppError
from movie_scheduler.features.show.repository import movie_show_repository
from movie_scheduler.features.show.service import show_service


@pytest.mark.parametrize("label", ["wished", "skipped", "watched", None])
def test_set_label_updates_wishes_and_show_cache(monkeypatch: MonkeyPatch, label: str | None) -> None:
    request = SetMovieLabelRequest.model_validate({"label": label})
    write = Mock(return_value=True)
    refresh = AsyncMock()
    delete = Mock()
    movie = Movie.from_dict({"id": 123, "title": "电影", "is_wished": label == "wished", "is_skipped": label == "skipped", "is_watched": label == "watched"})
    monkeypatch.setattr(movie_repository, "set_movie_label", write)
    monkeypatch.setattr(movie_repository, "get_movie_by_id", Mock(return_value=movie))
    monkeypatch.setattr(show_service, "refresh_movie_shows", refresh)
    monkeypatch.setattr(movie_show_repository, "delete_for_movie", delete)
    result = asyncio.run(MovieService().set_movie_label(123, request))
    assert result["is_wished"] == (label == "wished")
    assert result["is_skipped"] == (label == "skipped")
    assert result["is_watched"] == (label == "watched")
    assert refresh.call_count == int(label == "wished")
    assert delete.call_count == int(label != "wished")


def test_set_label_missing_movie(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(movie_repository, "set_movie_label", Mock(return_value=False))
    with pytest.raises(AppError) as error:
        asyncio.run(MovieService().set_movie_label(999, SetMovieLabelRequest(label="skipped")))
    assert error.value.status_code == 404


def test_create_manual_movie_uses_local_id_and_wish_state(monkeypatch: MonkeyPatch) -> None:
    create = Mock(side_effect=Movie.from_dict)
    monkeypatch.setattr(movie_repository, "create_manual_movie", create)
    result = asyncio.run(MovieService().create_manual_movie(CreateManualMovieRequest(title=" 手动电影 ")))
    data = create.call_args.args[0]
    assert -(2**52) <= data["id"] < 0
    assert data["title"] == "手动电影"
    assert result["is_wished"] is True
