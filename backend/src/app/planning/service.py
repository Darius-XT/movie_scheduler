"""排片计划业务服务。"""

from __future__ import annotations

import asyncio
from typing import cast

from app.models.planning import PlanningItem as PlanningItemModel
from app.models.planning import PlanningItemWriteData
from app.planning.schemas import PlanningData, PlanningItem, PlanningListType
from app.repositories.planning import planning_repository


class PlanningService:
    """单用户想看与行程计划服务。"""

    async def get_planning(self) -> PlanningData:
        """读取当前排片计划。"""
        items = await asyncio.to_thread(planning_repository.list_items)
        return self._build_planning_data(items)

    async def replace_planning(
        self,
        wish_pool: list[PlanningItem],
        schedule_items: list[PlanningItem],
    ) -> PlanningData:
        """全量替换当前排片计划。"""
        write_items = [
            *[self._to_write_data("wish", item) for item in wish_pool],
            *[self._to_write_data("schedule", item) for item in schedule_items],
        ]
        saved_items = await asyncio.to_thread(planning_repository.replace_all, write_items)
        return self._build_planning_data(saved_items)

    def _to_write_data(self, list_type: PlanningListType, item: PlanningItem) -> PlanningItemWriteData:
        return {
            "list_type": list_type,
            "show_key": item.key,
            "movie_id": item.movie_id,
            "movie_title": item.movie_title,
            "date": item.date,
            "time": item.time,
            "cinema_id": item.cinema_id,
            "cinema_name": item.cinema_name,
            "price": item.price,
            "duration_minutes": item.duration_minutes,
            "purchased": item.purchased if list_type == "schedule" else False,
        }

    def _build_planning_data(self, items: list[PlanningItemModel]) -> PlanningData:
        wish_pool: list[PlanningItem] = []
        schedule_items: list[PlanningItem] = []
        for item in items:
            planning_item = self._to_schema_item(item)
            list_type = cast(str, getattr(item, "list_type"))
            if list_type == "schedule":
                schedule_items.append(planning_item)
            elif list_type == "wish":
                wish_pool.append(planning_item)
        return PlanningData(wish_pool=wish_pool, schedule_items=schedule_items)

    def _to_schema_item(self, item: PlanningItemModel) -> PlanningItem:
        return PlanningItem(
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
