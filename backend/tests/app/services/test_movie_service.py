"""电影服务测试。"""

from __future__ import annotations

import pytest

from app.core.exceptions import AppError
from app.services.movie_selection.result_builder import MovieSelectionItem
from app.services.movie_selection.service import movie_service


@pytest.mark.anyio
async def test_movie_service_uses_default_selection_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """未传上映状态时应回退到全部模式。"""

    def select_all(selection_mode: str) -> list[MovieSelectionItem]:
        assert selection_mode == "all"
        return [
            MovieSelectionItem(
                id=1, title=None, score=None, douban_url=None, genres=None, actors=None,
                release_date=None, is_showing=False, director=None, country=None,
                language=None, duration=None, description=None, first_seen_at=None,
            )
        ]

    monkeypatch.setattr(movie_service.selector, "select_movie", select_all)
    result = await movie_service.select_movie()

    assert len(result) == 1
    assert result[0].id == 1


def test_movie_service_rejects_invalid_selection_mode() -> None:
    """无效的上映状态筛选值应被拒绝。"""
    with pytest.raises(AppError):
        movie_service._normalize_selection_mode("invalid")  # pyright: ignore[reportPrivateUsage, reportArgumentType]
