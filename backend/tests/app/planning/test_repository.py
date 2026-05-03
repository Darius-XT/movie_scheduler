"""排片计划仓储测试。"""

from __future__ import annotations

from typing import cast

from app.models.planning import PlanningItemWriteData
from app.repositories.planning import PlanningRepository


def _item(show_key: str, list_type: str = "wish", purchased: bool = False) -> PlanningItemWriteData:
    return {
        "list_type": list_type,
        "show_key": show_key,
        "movie_id": 1,
        "movie_title": "测试电影",
        "date": "2026-05-03",
        "time": "19:30",
        "cinema_id": 10,
        "cinema_name": "测试影院",
        "price": "39.9",
        "duration_minutes": 120,
        "purchased": purchased,
    }


def test_replace_all_replaces_existing_items() -> None:
    """全量保存应替换旧计划。"""
    repository = PlanningRepository()

    repository.replace_all([_item("old")])
    repository.replace_all([_item("new", "schedule", purchased=True)])

    items = repository.list_items()
    assert len(items) == 1
    assert cast(str, getattr(items[0], "show_key")) == "new"
    assert cast(str, getattr(items[0], "list_type")) == "schedule"
    assert cast(bool, getattr(items[0], "purchased")) is True


def test_same_show_key_can_exist_in_different_lists() -> None:
    """同一场次可同时位于想看和行程。"""
    repository = PlanningRepository()

    repository.replace_all([_item("same", "wish"), _item("same", "schedule", purchased=True)])

    items = repository.list_items()
    assert [
        (cast(str, getattr(item, "list_type")), cast(str, getattr(item, "show_key")))
        for item in items
    ] == [("wish", "same"), ("schedule", "same")]
