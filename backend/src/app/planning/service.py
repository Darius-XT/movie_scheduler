"""排片计划业务服务。"""

from __future__ import annotations

import asyncio
from typing import cast

from app.models.planning import PlanningItem as PlanningItemModel
from app.models.planning import PlanningItemWriteData
from app.planning.schemas import PlanningData, ScheduleItem
from app.repositories.planning import planning_repository


class PlanningService:
    """单用户行程计划服务。"""

    async def get_planning(self) -> PlanningData:
        """读取当前行程。"""
        items = await asyncio.to_thread(planning_repository.list_items)
        return PlanningData(schedule_items=[self._to_schema_item(item) for item in items])

    async def replace_schedule_items(
        self,
        schedule_items: list[ScheduleItem],
    ) -> PlanningData:
        """全量替换行程。"""
        write_items = [self._to_write_data(item) for item in schedule_items]
        saved_items = await asyncio.to_thread(planning_repository.replace_all, write_items)
        return PlanningData(schedule_items=[self._to_schema_item(item) for item in saved_items])

    def _to_write_data(self, item: ScheduleItem) -> PlanningItemWriteData:
        return {
            "show_key": item.key,
            "movie_id": item.movie_id,
            "movie_title": item.movie_title,
            "date": item.date,
            "time": item.time,
            "cinema_id": item.cinema_id,
            "cinema_name": item.cinema_name,
            "price": item.price,
            "duration_minutes": item.duration_minutes,
            "purchased": item.purchased,
        }

    def _to_schema_item(self, item: PlanningItemModel) -> ScheduleItem:
        return ScheduleItem(
            key=cast(str, getattr(item, "show_key")),
            movieId=cast(int, getattr(item, "movie_id")),
            movieTitle=cast(str, getattr(item, "movie_title")),
            date=cast(str, getattr(item, "date")),
            time=cast(str, getattr(item, "time")),
            cinemaId=cast(int, getattr(item, "cinema_id")),
            cinemaName=cast(str, getattr(item, "cinema_name")),
            price=cast(str | None, getattr(item, "price")),
            durationMinutes=cast(int | None, getattr(item, "duration_minutes")),
            purchased=cast(bool, getattr(item, "purchased")),
        )


planning_service = PlanningService()
