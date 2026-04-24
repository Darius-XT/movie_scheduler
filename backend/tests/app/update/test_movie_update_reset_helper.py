"""电影更新重置辅助测试。"""

from __future__ import annotations

import importlib

import pytest

from app.update.movie_update_reset_helper import MovieUpdateResetHelper

movie_repository_module = importlib.import_module("app.repositories.movie")


def test_reset_helper_deletes_movies_when_force_update(monkeypatch: pytest.MonkeyPatch) -> None:
    """强制全量更新时应触发删除。"""
    called = {"delete_all_movies": 0}

    def delete_all_movies() -> bool:
        called["delete_all_movies"] += 1
        return True

    monkeypatch.setattr(movie_repository_module.movie_repository, "delete_all_movies", delete_all_movies)

    helper = MovieUpdateResetHelper()
    helper.reset_movies_if_needed(True)

    assert called["delete_all_movies"] == 1


def test_reset_helper_skips_delete_when_not_force_update(monkeypatch: pytest.MonkeyPatch) -> None:
    """非强制全量更新时不应触发删除。"""
    called = {"delete_all_movies": 0}

    def delete_all_movies() -> bool:
        called["delete_all_movies"] += 1
        return True

    monkeypatch.setattr(movie_repository_module.movie_repository, "delete_all_movies", delete_all_movies)

    helper = MovieUpdateResetHelper()
    helper.reset_movies_if_needed(False)

    assert called["delete_all_movies"] == 0
