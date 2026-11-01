import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from pytest import MonkeyPatch

from movie_scheduler.features.movie.models import Movie
from movie_scheduler.features.movie.repository import movie_repository
from movie_scheduler.features.movie.schemas import CreateManualMovieRequest, SetMovieChannelsRequest, SetMovieLabelRequest
from movie_scheduler.features.movie.service import MovieService
from movie_scheduler.core.exceptions import AppError, MaoyanVerificationError
import movie_scheduler.features.movie.service as movie_module
from movie_scheduler.features.show.repository import movie_show_repository
from movie_scheduler.features.show.service import show_service
from movie_scheduler.features.movie.schemas import SetMovieViewingLocationRequest


@pytest.mark.parametrize("location", ["home", "cinema", None])
def test_set_viewing_location(monkeypatch: MonkeyPatch, location: str | None) -> None:
    movie = Movie.from_dict({"id": 1, "title": "电影", "viewing_location": location, "is_wished": True})
    write = Mock(return_value=movie)
    monkeypatch.setattr(movie_repository, "set_movie_viewing_location", write)
    refresh = AsyncMock()
    monkeypatch.setattr(show_service, "refresh_movie_shows", refresh)
    request = SetMovieViewingLocationRequest.model_validate({"viewing_location": location})
    result = asyncio.run(MovieService().set_movie_viewing_location(1, request))
    write.assert_called_once_with({"id": 1, "viewing_location": location})
    assert result["viewing_location"] == location
    assert refresh.call_count == int(location == "cinema")
    assert result["is_wished"] is True
    write.return_value = None
    with pytest.raises(AppError) as error:
        asyncio.run(MovieService().set_movie_viewing_location(999, request))
    assert error.value.status_code == 404


def test_set_movie_channels_and_handles_missing_movie(monkeypatch: MonkeyPatch) -> None:
    movie = Movie.from_dict({"id": 1, "title": "老片", "channels": ["bilibili"], "is_wished": True})
    write = Mock(return_value=movie)
    monkeypatch.setattr(movie_repository, "set_movie_channels", write)
    request = SetMovieChannelsRequest(channels=["bilibili"])
    result = asyncio.run(MovieService().set_movie_channels(1, request))
    write.assert_called_once_with({"id": 1, "channels": ["bilibili"]})
    assert result["channels"] == ["bilibili"]
    assert result["is_wished"] is True
    write.return_value = None
    with pytest.raises(AppError) as error:
        asyncio.run(MovieService().set_movie_channels(999, request))
    assert error.value.status_code == 404


@pytest.mark.parametrize("label", ["wished", "skipped", "watched", None])
@pytest.mark.parametrize("location", ["cinema", "home", None])
def test_set_label_updates_wishes_and_show_cache(monkeypatch: MonkeyPatch, label: str | None, location: str | None) -> None:
    request = SetMovieLabelRequest.model_validate({"label": label})
    write = Mock(return_value=True)
    refresh = AsyncMock()
    delete = Mock()
    movie = Movie.from_dict({"id": 123, "title": "电影", "viewing_location": location, "is_wished": label == "wished", "is_skipped": label == "skipped", "is_watched": label == "watched"})
    monkeypatch.setattr(movie_repository, "set_movie_label", write)
    monkeypatch.setattr(movie_repository, "get_movie_by_id", Mock(return_value=movie))
    monkeypatch.setattr(show_service, "refresh_movie_shows", refresh)
    monkeypatch.setattr(movie_show_repository, "delete_for_movie", delete)
    result = asyncio.run(MovieService().set_movie_label(123, request))
    assert result["is_wished"] == (label == "wished")
    assert result["is_skipped"] == (label == "skipped")
    assert result["is_watched"] == (label == "watched")
    assert refresh.call_count == int(label == "wished" and location == "cinema")
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


@pytest.mark.parametrize("stage", ["base", "extra"])
def test_movie_stream_reports_verification_without_completing(monkeypatch: MonkeyPatch, stage: str) -> None:
    base = Mock(side_effect=MaoyanVerificationError() if stage == "base" else None)
    extra = AsyncMock(side_effect=MaoyanVerificationError() if stage == "extra" else None)
    touch = Mock()
    monkeypatch.setattr(movie_module.update_base_service, "update_all", base)
    monkeypatch.setattr(movie_module.update_extra_service, "update_all", extra)
    monkeypatch.setattr(movie_repository, "touch_movies_last_updated_at", touch)

    async def collect() -> list[str]:
        return [frame async for frame in MovieService().stream_movie_update(10)]

    frames = asyncio.run(collect())
    assert any('"type":"error"' in frame and "已停止本轮剩余抓取" in frame for frame in frames)
    assert not any('"type":"complete"' in frame for frame in frames)
    touch.assert_not_called()
    assert extra.await_count == int(stage == "extra")


def test_scheduled_movie_verification_propagates_without_timestamp(monkeypatch: MonkeyPatch) -> None:
    service = MovieService()
    touch = Mock()
    monkeypatch.setattr(service, "update_movies", AsyncMock(side_effect=MaoyanVerificationError()))
    monkeypatch.setattr(movie_repository, "touch_movies_last_updated_at", touch)
    with pytest.raises(MaoyanVerificationError):
        asyncio.run(service.refresh_all_movies())
    touch.assert_not_called()
