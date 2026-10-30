from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from movie_scheduler.features.movie.router import router
from movie_scheduler.features.movie.service import movie_service


def test_create_manual_movie(monkeypatch: MonkeyPatch) -> None:
    create = AsyncMock(return_value={"id": -123, "title": "未收录电影", "is_wished": True})
    monkeypatch.setattr(movie_service, "create_manual_movie", create)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    response = TestClient(app).post("/api/movies/manual", json={"title": " 未收录电影 "})
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["movie"]["is_wished"] is True
    assert create.call_args.args[0].title == "未收录电影"


@pytest.mark.parametrize("title", ["", "   ", "\n\t", "影" * 201])
def test_create_manual_movie_rejects_invalid_title(monkeypatch: MonkeyPatch, title: str) -> None:
    create = AsyncMock()
    monkeypatch.setattr(movie_service, "create_manual_movie", create)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    assert TestClient(app).post("/api/movies/manual", json={"title": title}).status_code == 422
    create.assert_not_called()
