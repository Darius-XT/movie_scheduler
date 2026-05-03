"""排片计划服务测试。"""

from __future__ import annotations

import pytest

from app.planning.schemas import PlanningItem
from app.planning.service import PlanningService


def _schema_item(purchased: bool = False) -> PlanningItem:
    return PlanningItem(
        key="1-10-2026-05-03-19:30",
        movieId=1,
        movieTitle="测试电影",
        date="2026-05-03",
        time="19:30",
        cinemaId=10,
        cinemaName="测试影院",
        price="39.9",
        durationMinutes=120,
        purchased=purchased,
    )


@pytest.mark.anyio
async def test_replace_planning_normalizes_wish_purchased() -> None:
    """想看条目不保留已购票状态，行程条目保留。"""
    service = PlanningService()

    data = await service.replace_planning(
        wish_pool=[_schema_item(purchased=True)],
        schedule_items=[_schema_item(purchased=True)],
    )

    assert data.wish_pool[0].purchased is False
    assert data.schedule_items[0].purchased is True
