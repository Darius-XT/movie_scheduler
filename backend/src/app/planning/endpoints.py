"""排片计划接口。"""

from __future__ import annotations

from fastapi import APIRouter

from app.planning.schemas import PlanningResponse, ReplacePlanningRequest
from app.planning.service import planning_service

router = APIRouter()


@router.get("/planning", response_model=PlanningResponse)
async def get_planning() -> PlanningResponse:
    """读取单用户排片计划。"""
    data = await planning_service.get_planning()
    return PlanningResponse(data=data)


@router.put("/planning", response_model=PlanningResponse)
async def replace_planning(request: ReplacePlanningRequest) -> PlanningResponse:
    """全量替换单用户排片计划。"""
    data = await planning_service.replace_planning(
        wish_pool=request.wish_pool,
        schedule_items=request.schedule_items,
    )
    return PlanningResponse(data=data)
