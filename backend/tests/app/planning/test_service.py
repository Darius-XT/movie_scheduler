"""排片计划服务测试。"""

from __future__ import annotations

import pytest

from app.planning.schemas import ScheduleItem
from app.planning.service import PlanningService


def _schema_item(purchased: bool = False) -> ScheduleItem:
    return ScheduleItem(
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
async def test_replace_schedule_items_persists_purchased_flag() -> None:
    """行程条目的 purchased 字段应被原样持久化。"""
    service = PlanningService()

    data = await service.replace_schedule_items(
        schedule_items=[_schema_item(purchased=True)],
    )

    assert len(data.schedule_items) == 1
    assert data.schedule_items[0].purchased is True
