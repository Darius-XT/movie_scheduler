"""城市接口。"""

from fastapi import APIRouter

from app.city.schemas import CityItem, CityListData, CityListResponse
from app.city.service import city_service

router = APIRouter()


@router.get("/cities", response_model=CityListResponse)
async def get_cities() -> CityListResponse:
    """返回可用城市列表。"""
    cities = [CityItem(name=item.name, id=item.id) for item in city_service.list_city()]
    return CityListResponse(data=CityListData(cities=cities))
