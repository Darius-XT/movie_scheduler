"""排片计划接口。"""

from __future__ import annotations

from fastapi import APIRouter

from app.planning.schemas import PlanningResponse, ReplaceScheduleItemsRequest
from app.planning.service import planning_service

router = APIRouter()


@router.get("/planning", response_model=PlanningResponse)
async def get_planning() -> PlanningResponse:
    """读取行程列表。"""
    data = await planning_service.get_planning()
    return PlanningResponse(data=data)


@router.put("/planning/schedule-items", response_model=PlanningResponse)
async def replace_schedule_items(request: ReplaceScheduleItemsRequest) -> PlanningResponse:
    """全量替换行程列表。"""
    data = await planning_service.replace_schedule_items(schedule_items=request.schedule_items)
    return PlanningResponse(data=data)
